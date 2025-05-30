// ==UserScript==
// @name         YouTube Playlist Tracker with Drag Button and UI Output
// @namespace    http://tampermonkey.net/
// @version      1.7
// @description  增量记录YouTube播放列表视频，智能缺失检测，带可拖动按钮和页面展示结果
// @match        https://www.youtube.com/playlist?list=*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    let STORAGE_KEY = '';

    function getVideoItems() {
        const renderers = document.querySelectorAll('ytd-playlist-video-renderer');
        const items = [];
        for (let i = 0; i < renderers.length; i++) {
            const renderer = renderers[i];
            const a = renderer.querySelector('a#video-title');
            const shape = renderer.querySelector('.badge-shape-wiz__text');
            const time = shape ? shape.textContent.trim() : null;
            const title = a.textContent.trim();
            const rawHref = a.getAttribute('href');
            if (!rawHref) continue;
            const href = 'https://www.youtube.com' + rawHref.substring(0, rawHref.indexOf("&"));
            if (!title || !href || title.indexOf("已删除视频") > -1) continue;
            // 提取日期
            const dateMatch = title.match(/202\d{5}/);
            let liveDate = null;
            if (dateMatch) {
                const rawDate = dateMatch[0];
                liveDate = rawDate.slice(0, 4) + '-' + rawDate.slice(4, 6) + '-' + rawDate.slice(6, 8);
            }
            // 提取视频 ID
            const id = href.substring(href.indexOf("v=") + 2);
            // 提取视频 index
            let index = rawHref.indexOf("index=") + 6
            index = rawHref.substring(index, rawHref.indexOf("&", index));
            items.push({
                title: title,
                href: href,
                liveDate: liveDate,
                id: id,
                index: index,
                time: time
            });
        }
        return items;
    }

    function loadStoredItems() {
        const data = localStorage.getItem(STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    }

    function saveStoredItems(items) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    }

    function removeStoredItem(href) {
        const items = loadStoredItems();
        for (let i = 0; i < items.length; i++) {
            if (items[i].href === href) {
                items[i].hide = true;
            }
        }
        saveStoredItems(items);
        checkVideos();
    }

    function compareItems(stored, current) {
        const currentHrefs = new Set(current.map(item => item.href));
        const addedItems = current.filter(item => !stored.some(s => s.href === item.href));

        const removedItems = [];
        for (let i = 1; i < stored.length - 1; i++) {
            const prev = stored[i - 1];
            const currentItem = stored[i];
            const next = stored[i + 1];

            const isMissing = !currentHrefs.has(currentItem.href);
            const neighborsPresent = currentHrefs.has(prev.href) && currentHrefs.has(next.href);

            if (isMissing && neighborsPresent && !currentItem.hide) {
                removedItems.push(currentItem);
            }
        }

        return { addedItems, removedItems };
    }

    function renderOutput({ addedItems, removedItems, currentItems, storedItems }) {
        const output = document.getElementById('video-check-output');
        while (output.firstChild) {
            output.removeChild(output.firstChild);
        }

        const createSection = (title, items, color, showRemove = false) => {
            const section = document.createElement('div');
            section.style.marginBottom = '10px';

            const header = document.createElement('div');
            header.textContent = title;
            header.style.fontWeight = 'bold';
            header.style.color = color;
            section.appendChild(header);

            if (items === null) {
                const empty = document.createElement('div');
                section.appendChild(empty);
            } else if (items.length === 0) {
                const empty = document.createElement('div');
                empty.textContent = '无';
                section.appendChild(empty);
            } else {
                items.forEach(item => {
                    const line = document.createElement('div');
                    line.style.display = 'flex';
                    line.style.justifyContent = 'space-between';
                    line.style.alignItems = 'center';

                    const titleSpan = document.createElement('span');
                    const fullTitle = (item.liveDate ? item.liveDate + "_" : '') + item.title;
                    titleSpan.textContent = fullTitle.length > 20 ? fullTitle.slice(0, 20) + '…' : fullTitle;
                    titleSpan.title = fullTitle;
                    line.appendChild(titleSpan);

                    if (showRemove) {
                        const removeBtn = document.createElement('button');
                        removeBtn.textContent = '清除';
                        removeBtn.style.marginLeft = '10px';
                        removeBtn.style.padding = '2px 6px';
                        removeBtn.style.fontSize = '12px';
                        removeBtn.style.cursor = 'pointer';
                        removeBtn.addEventListener('click', () => removeStoredItem(item.href));
                        line.appendChild(removeBtn);
                    }

                    section.appendChild(line);
                });
            }
            return section;
        };

        output.appendChild(createSection('🗓 列表数量：' + currentItems.length, null, 'blue'));
        output.appendChild(createSection('🗒 历史数量：' + storedItems.length, null, 'blue'));
        output.appendChild(createSection('🚫 缺失视频：' + removedItems.length, removedItems, 'red', true));
        output.appendChild(createSection('🆕 新增视频：' + addedItems.length, addedItems, 'green'));
    }

    function checkVideos(button = null) {
        if (button) {
            button.style.backgroundColor = '#444'; // 点击后变色
        }

        let playlist_name = document.querySelector('yt-dynamic-text-view-model.page-header-view-model-wiz__page-header-title span').innerText;

        STORAGE_KEY = 'yt_playlist_' + playlist_name.replace(/ /g, "_");

        const currentItems = getVideoItems();
        const storedItems = loadStoredItems();

        const { addedItems, removedItems } = compareItems(storedItems, currentItems);
        renderOutput({ addedItems, removedItems, currentItems, storedItems });

        if (addedItems.length > 0) {
            let updated = [...storedItems];
            for (const item of addedItems) {
                if (!updated.find(stored => stored.href === item.href)) {
                    updated.push(item);
                }
            }
            updated = updated.sort((a, b) => {
                if (a.index && b.index) {
                    return a.index - b.index;
                } else if (a.liveDate && b.liveDate) {
                    return b.liveDate.localeCompare(a.liveDate);
                } else if (a.title && b.title) {
                    return b.title.localeCompare(a.title);
                }
                return b.href.localeCompare(a.href);
            });
            saveStoredItems(updated);
        }
    }

    function addCheckUI() {
        // 容器
        const wrapper = document.createElement('div');
        wrapper.style.position = 'fixed';
        wrapper.style.bottom = '20px';
        wrapper.style.right = '20px';
        wrapper.style.zIndex = 9999;

        // 按钮
        const btn = document.createElement('button');
        btn.textContent = '📋 检查视频列表';
        btn.style.padding = '10px 15px';
        btn.style.backgroundColor = '#0f0f0f';
        btn.style.color = 'white';
        btn.style.border = '1px solid #aaa';
        btn.style.borderRadius = '8px';
        btn.style.cursor = 'move';
        btn.style.fontSize = '14px';
        btn.style.boxShadow = '0 2px 6px rgba(0,0,0,0.2)';
        btn.style.marginBottom = '8px';
        btn.draggable = true;

        // 拖动功能
        let offsetX = 0, offsetY = 0;
        btn.addEventListener('dragstart', (e) => {
            offsetX = e.offsetX;
            offsetY = e.offsetY;
        });
        btn.addEventListener('dragend', (e) => {
            wrapper.style.left = `${e.pageX - offsetX}px`;
            wrapper.style.top = `${e.pageY - offsetY}px`;
            wrapper.style.bottom = 'auto';
            wrapper.style.right = 'auto';
            wrapper.style.position = 'fixed';
        });

        // 结果区域
        const output = document.createElement('div');
        output.id = 'video-check-output';
        output.style.backgroundColor = 'white';
        output.style.color = 'black';
        output.style.padding = '10px';
        output.style.maxHeight = '300px';
        output.style.overflowY = 'auto';
        output.style.minWidth = '250px';
        output.style.fontSize = '13px';
        output.style.border = '1px solid #ccc';
        output.style.borderRadius = '6px';
        output.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';

        btn.addEventListener('click', () => {
            console.log('🔍 手动触发检查...');
            clearTimeout(timeout);
            checkVideos(btn);
        });

        wrapper.appendChild(btn);
        wrapper.appendChild(output);
        document.body.appendChild(wrapper);
    }

    const timeout = setTimeout(() => {
        console.log('⏱ 自动检查视频列表（10秒延迟）...');
        checkVideos();
    }, 10000);

    window.addEventListener('load', addCheckUI);
})();
