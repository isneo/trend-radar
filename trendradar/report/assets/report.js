// ===== 浏览器增强功能 =====

function toggleWideMode() {
    document.body.classList.toggle('wide-mode');
    var isWide = document.body.classList.contains('wide-mode');
    try { localStorage.setItem('trendradar-wide-mode', isWide ? '1' : '0'); } catch(e) {}
    var btn = document.querySelector('.toggle-wide-btn');
    if (btn) btn.textContent = isWide ? '⊡' : '⛶';
    initTabVisibility();
    initCollapseVisibility();
    initStandaloneTabVisibility();
}

function toggleDarkMode() {
    var isDark = document.body.classList.toggle('dark-mode');
    try { localStorage.setItem('trendradar-dark-mode', isDark ? '1' : '0'); } catch(e) {}
    var btn = document.querySelector('.toggle-dark-btn');
    if (btn) btn.textContent = isDark ? '☀' : '☽';
}

function initTabs() {
    var tabBar = document.querySelector('.tab-bar');
    if (!tabBar) return;
    var tabs = tabBar.querySelectorAll('.tab-btn');
    var groups = document.querySelectorAll('.word-group[data-tab-index]');
    initTabVisibility();

    function activateTab(index) {
        tabs.forEach(function(t) { t.classList.remove('active'); });
        if (index === 'all') {
            var allBtn = tabBar.querySelector('[data-tab-index="all"]');
            if (allBtn) allBtn.classList.add('active');
            groups.forEach(function(g) { g.style.display = ''; });
            try { history.replaceState(null, '', '#all'); } catch(e) {}
            return;
        }
        var idx = parseInt(index);
        tabs.forEach(function(t) {
            if (parseInt(t.dataset.tabIndex) === idx) t.classList.add('active');
        });
        if (document.body.classList.contains('wide-mode') && !tabBar.classList.contains('tab-hidden')) {
            groups.forEach(function(g) {
                g.style.display = (parseInt(g.dataset.tabIndex) === idx) ? '' : 'none';
            });
        }
        try { history.replaceState(null, '', '#tab-' + idx); } catch(e) {}
    }

    tabs.forEach(function(tab) {
        tab.addEventListener('click', function() {
            var idx = tab.dataset.tabIndex;
            activateTab(idx === 'all' ? 'all' : parseInt(idx));
        });
    });

    tabBar.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
            var tabsArr = Array.from(tabs);
            var ci = tabsArr.findIndex(function(t) { return t.classList.contains('active'); });
            var dir = e.key === 'ArrowRight' ? 1 : -1;
            var ni = Math.max(0, Math.min(tabsArr.length - 1, ci + dir));
            var nt = tabsArr[ni];
            activateTab(nt.dataset.tabIndex === 'all' ? 'all' : parseInt(nt.dataset.tabIndex));
            nt.focus();
            e.preventDefault();
        }
    });

    var hash = window.location.hash;
    if (hash === '#all') { activateTab('all'); }
    else if (hash.indexOf('#tab-') === 0) { activateTab(parseInt(hash.replace('#tab-', ''))); }
    else { activateTab(0); }
}

function initTabVisibility() {
    var tabBar = document.querySelector('.tab-bar');
    if (!tabBar) return;
    var groups = document.querySelectorAll('.word-group[data-tab-index]');
    var isWide = document.body.classList.contains('wide-mode');
    if (!isWide || groups.length <= 2) {
        tabBar.classList.add('tab-hidden');
        groups.forEach(function(g) { g.style.display = ''; });
    } else {
        tabBar.classList.remove('tab-hidden');
        var activeTab = tabBar.querySelector('.tab-btn.active');
        if (activeTab) { activeTab.click(); }
        else {
            var firstTab = tabBar.querySelector('.tab-btn');
            if (firstTab) firstTab.click();
        }
    }
}

function handleSearch(query) {
    query = query.toLowerCase();
    document.querySelectorAll('.news-item').forEach(function(item) {
        var title = (item.querySelector('.news-title') || {}).textContent || '';
        item.style.display = (!query || title.toLowerCase().indexOf(query) !== -1) ? '' : 'none';
    });
    document.querySelectorAll('.rss-item').forEach(function(item) {
        var title = (item.querySelector('.rss-title') || {}).textContent || '';
        item.style.display = (!query || title.toLowerCase().indexOf(query) !== -1) ? '' : 'none';
    });
}

function initBackToTop() {
    var fabBar = document.querySelector('.fab-bar');
    if (!fabBar) return;
    window.addEventListener('scroll', function() {
        fabBar.classList.toggle('visible', window.scrollY > 300);
    });
}

function initCollapse() {
    document.querySelectorAll('.word-header').forEach(function(header) {
        header.addEventListener('click', function() {
            var tabBar = document.querySelector('.tab-bar');
            if (document.body.classList.contains('wide-mode') && tabBar && !tabBar.classList.contains('tab-hidden')) return;
            var group = header.closest('.word-group');
            if (group) group.classList.toggle('collapsed');
        });
    });
    initCollapseVisibility();
}

function initCollapseVisibility() {
    var headers = document.querySelectorAll('.word-header');
    var tabBar = document.querySelector('.tab-bar');
    var isTabMode = document.body.classList.contains('wide-mode') && tabBar && !tabBar.classList.contains('tab-hidden');
    headers.forEach(function(h) {
        if (isTabMode) { h.classList.remove('collapsible'); }
        else { h.classList.add('collapsible'); }
    });
    if (isTabMode) {
        document.querySelectorAll('.word-group.collapsed').forEach(function(g) {
            g.classList.remove('collapsed');
        });
    }
}

// 独立展示区 Tab 切换
function initStandaloneTabs() {
    var tabBar = document.querySelector('.standalone-tab-bar');
    if (!tabBar) return;
    var groups = document.querySelectorAll('.standalone-group[data-standalone-tab]');
    var btns = tabBar.querySelectorAll('.tab-btn[data-standalone-tab]');

    function activateStandaloneTab(val) {
        btns.forEach(function(b) {
            var bVal = b.getAttribute('data-standalone-tab');
            b.classList.toggle('active', bVal === String(val));
        });
        groups.forEach(function(g) {
            var gVal = g.getAttribute('data-standalone-tab');
            g.style.display = (val === 'all' || gVal === String(val)) ? '' : 'none';
        });
    }

    btns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            activateStandaloneTab(btn.getAttribute('data-standalone-tab'));
        });
    });

    // 初始状态
    initStandaloneTabVisibility();
}

function initStandaloneTabVisibility() {
    var tabBar = document.querySelector('.standalone-tab-bar');
    if (!tabBar) return;
    var groups = document.querySelectorAll('.standalone-group[data-standalone-tab]');
    var isWide = document.body.classList.contains('wide-mode');
    if (!isWide || groups.length <= 1) {
        tabBar.classList.add('tab-hidden');
        groups.forEach(function(g) { g.style.display = ''; });
    } else {
        tabBar.classList.remove('tab-hidden');
        var activeBtn = tabBar.querySelector('.tab-btn.active');
        if (activeBtn) activeBtn.click();
        else { var first = tabBar.querySelector('.tab-btn'); if (first) first.click(); }
    }
}

function prepareForScreenshot() {
    var state = {
        wasWide: document.body.classList.contains('wide-mode'),
        hiddenGroups: []
    };
    document.body.classList.remove('wide-mode');
    state.wasDark = document.body.classList.contains('dark-mode');
    document.body.classList.remove('dark-mode');
    document.querySelectorAll('.word-group[data-tab-index]').forEach(function(g, i) {
        if (g.style.display === 'none') {
            state.hiddenGroups.push(i);
            g.style.display = '';
        }
    });
    state.hiddenStandaloneGroups = [];
    document.querySelectorAll('.standalone-group[data-standalone-tab]').forEach(function(g, i) {
        if (g.style.display === 'none') {
            state.hiddenStandaloneGroups.push(i);
            g.style.display = '';
        }
    });
    document.querySelectorAll('.tab-bar, .standalone-tab-bar, .search-bar, .fab-bar, .toggle-wide-btn').forEach(function(el) {
        el.dataset.prevDisplay = el.style.display || '';
        el.style.display = 'none';
    });
    document.querySelectorAll('.toggle-dark-btn').forEach(function(el) {
        el.dataset.prevDisplay = el.style.display || ''; el.style.display = 'none';
    });
    document.querySelectorAll('.reading-progress').forEach(function(el) { el.style.display = 'none'; });
    document.querySelectorAll('.header-watermark').forEach(function(el) { el.style.display = 'none'; });
    return state;
}

function restoreAfterScreenshot(state) {
    if (state.wasWide) document.body.classList.add('wide-mode');
    if (state.wasDark) document.body.classList.add('dark-mode');
    var groups = document.querySelectorAll('.word-group[data-tab-index]');
    state.hiddenGroups.forEach(function(i) {
        if (groups[i]) groups[i].style.display = 'none';
    });
    var standaloneGroups = document.querySelectorAll('.standalone-group[data-standalone-tab]');
    if (state.hiddenStandaloneGroups) {
        state.hiddenStandaloneGroups.forEach(function(i) {
            if (standaloneGroups[i]) standaloneGroups[i].style.display = 'none';
        });
    }
    document.querySelectorAll('.tab-bar, .standalone-tab-bar, .search-bar, .fab-bar, .toggle-wide-btn').forEach(function(el) {
        el.style.display = el.dataset.prevDisplay || '';
        delete el.dataset.prevDisplay;
    });
    document.querySelectorAll('.toggle-dark-btn').forEach(function(el) {
        el.style.display = el.dataset.prevDisplay || ''; delete el.dataset.prevDisplay;
    });
    document.querySelectorAll('.reading-progress').forEach(function(el) { el.style.display = ''; });
    document.querySelectorAll('.reading-progress').forEach(function(el) { el.style.display = ''; });
    document.querySelectorAll('.header-watermark').forEach(function(el) { el.style.display = ''; });
    initTabVisibility();
    initCollapseVisibility();
    initStandaloneTabVisibility();
    var fabBar = document.querySelector('.fab-bar');
    if (fabBar && window.scrollY > 300) fabBar.classList.add('visible');
}

// ===== 截图功能 =====

async function saveAsImage() {
    const button = event.target;
    const originalText = button.textContent;

    try {
        button.textContent = '生成中...';
        button.disabled = true;
        window.scrollTo(0, 0);

        // 等待页面稳定
        await new Promise(resolve => setTimeout(resolve, 200));

        // 截图前准备：切回窄屏布局
        var screenshotState = prepareForScreenshot();

        // 截图前隐藏按钮
        const buttons = document.querySelector('.save-buttons');
        buttons.style.visibility = 'hidden';

        // 再次等待确保按钮完全隐藏
        await new Promise(resolve => setTimeout(resolve, 100));

        const container = document.querySelector('.container');

        const canvas = await html2canvas(container, {
            backgroundColor: '#ffffff',
            scale: 1.5,
            useCORS: true,
            allowTaint: false,
            imageTimeout: 10000,
            removeContainer: false,
            foreignObjectRendering: false,
            logging: false,
            width: container.offsetWidth,
            height: container.offsetHeight,
            x: 0,
            y: 0,
            scrollX: 0,
            scrollY: 0,
            windowWidth: window.innerWidth,
            windowHeight: window.innerHeight
        });

        buttons.style.visibility = 'visible';
        restoreAfterScreenshot(screenshotState);

        const link = document.createElement('a');
        const now = new Date();
        const filename = `TrendRadar_热点新闻分析_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}.png`;

        link.download = filename;
        link.href = canvas.toDataURL('image/png', 1.0);

        // 触发下载
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        button.textContent = '保存成功!';
        setTimeout(() => {
            button.textContent = originalText;
            button.disabled = false;
        }, 2000);

    } catch (error) {
        const buttons = document.querySelector('.save-buttons');
        buttons.style.visibility = 'visible';
        restoreAfterScreenshot(screenshotState);
        button.textContent = '保存失败';
        setTimeout(() => {
            button.textContent = originalText;
            button.disabled = false;
        }, 2000);
    }
}

async function saveAsMultipleImages() {
    const button = event.target;
    const originalText = button.textContent;
    const container = document.querySelector('.container');
    const scale = 1.5;
    const maxHeight = 5000 / scale;
    var screenshotState2 = prepareForScreenshot();

    try {
        button.textContent = '分析中...';
        button.disabled = true;

        // 获取所有可能的分割元素
        const newsItems = Array.from(container.querySelectorAll('.news-item'));
        const wordGroups = Array.from(container.querySelectorAll('.word-group'));
        const newSection = container.querySelector('.new-section');
        const errorSection = container.querySelector('.error-section');
        const header = container.querySelector('.header');
        const footer = container.querySelector('.footer');

        // 计算元素位置和高度
        const containerRect = container.getBoundingClientRect();
        const elements = [];

        // 添加header作为必须包含的元素
        elements.push({
            type: 'header',
            element: header,
            top: 0,
            bottom: header.offsetHeight,
            height: header.offsetHeight
        });

        // 添加错误信息（如果存在）
        if (errorSection) {
            const rect = errorSection.getBoundingClientRect();
            elements.push({
                type: 'error',
                element: errorSection,
                top: rect.top - containerRect.top,
                bottom: rect.bottom - containerRect.top,
                height: rect.height
            });
        }

        // 按word-group分组处理news-item
        wordGroups.forEach(group => {
            const groupRect = group.getBoundingClientRect();
            const groupNewsItems = group.querySelectorAll('.news-item');

            // 添加word-group的header部分
            const wordHeader = group.querySelector('.word-header');
            if (wordHeader) {
                const headerRect = wordHeader.getBoundingClientRect();
                elements.push({
                    type: 'word-header',
                    element: wordHeader,
                    parent: group,
                    top: groupRect.top - containerRect.top,
                    bottom: headerRect.bottom - containerRect.top,
                    height: headerRect.height
                });
            }

            // 添加每个news-item
            groupNewsItems.forEach(item => {
                const rect = item.getBoundingClientRect();
                elements.push({
                    type: 'news-item',
                    element: item,
                    parent: group,
                    top: rect.top - containerRect.top,
                    bottom: rect.bottom - containerRect.top,
                    height: rect.height
                });
            });
        });

        // 添加新增新闻部分
        if (newSection) {
            const rect = newSection.getBoundingClientRect();
            elements.push({
                type: 'new-section',
                element: newSection,
                top: rect.top - containerRect.top,
                bottom: rect.bottom - containerRect.top,
                height: rect.height
            });
        }

        // 添加footer
        const footerRect = footer.getBoundingClientRect();
        elements.push({
            type: 'footer',
            element: footer,
            top: footerRect.top - containerRect.top,
            bottom: footerRect.bottom - containerRect.top,
            height: footer.offsetHeight
        });

        // 计算分割点
        const segments = [];
        let currentSegment = { start: 0, end: 0, height: 0, includeHeader: true };
        let headerHeight = header.offsetHeight;
        currentSegment.height = headerHeight;

        for (let i = 1; i < elements.length; i++) {
            const element = elements[i];
            const potentialHeight = element.bottom - currentSegment.start;

            // 检查是否需要创建新分段
            if (potentialHeight > maxHeight && currentSegment.height > headerHeight) {
                // 在前一个元素结束处分割
                currentSegment.end = elements[i - 1].bottom;
                segments.push(currentSegment);

                // 开始新分段
                currentSegment = {
                    start: currentSegment.end,
                    end: 0,
                    height: element.bottom - currentSegment.end,
                    includeHeader: false
                };
            } else {
                currentSegment.height = potentialHeight;
                currentSegment.end = element.bottom;
            }
        }

        // 添加最后一个分段
        if (currentSegment.height > 0) {
            currentSegment.end = container.offsetHeight;
            segments.push(currentSegment);
        }

        button.textContent = `生成中 (0/${segments.length})...`;

        // 隐藏保存按钮
        const buttons = document.querySelector('.save-buttons');
        buttons.style.visibility = 'hidden';

        // 为每个分段生成图片
        const images = [];
        for (let i = 0; i < segments.length; i++) {
            const segment = segments[i];
            button.textContent = `生成中 (${i + 1}/${segments.length})...`;

            // 创建临时容器用于截图
            const tempContainer = document.createElement('div');
            tempContainer.style.cssText = `
                position: absolute;
                left: -9999px;
                top: 0;
                width: ${container.offsetWidth}px;
                background: white;
            `;
            tempContainer.className = 'container';

            // 克隆容器内容
            const clonedContainer = container.cloneNode(true);

            // 移除克隆内容中的保存按钮
            const clonedButtons = clonedContainer.querySelector('.save-buttons');
            if (clonedButtons) {
                clonedButtons.style.display = 'none';
            }

            tempContainer.appendChild(clonedContainer);
            document.body.appendChild(tempContainer);

            // 等待DOM更新
            await new Promise(resolve => setTimeout(resolve, 100));

            // 使用html2canvas截取特定区域
            const canvas = await html2canvas(clonedContainer, {
                backgroundColor: '#ffffff',
                scale: scale,
                useCORS: true,
                allowTaint: false,
                imageTimeout: 10000,
                logging: false,
                width: container.offsetWidth,
                height: segment.end - segment.start,
                x: 0,
                y: segment.start,
                windowWidth: window.innerWidth,
                windowHeight: window.innerHeight
            });

            images.push(canvas.toDataURL('image/png', 1.0));

            // 清理临时容器
            document.body.removeChild(tempContainer);
        }

        // 恢复按钮显示
        buttons.style.visibility = 'visible';

        // 下载所有图片
        const now = new Date();
        const baseFilename = `TrendRadar_热点新闻分析_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;

        for (let i = 0; i < images.length; i++) {
            const link = document.createElement('a');
            link.download = `${baseFilename}_part${i + 1}.png`;
            link.href = images[i];
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            // 延迟一下避免浏览器阻止多个下载
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        button.textContent = `已保存 ${segments.length} 张图片!`;
        restoreAfterScreenshot(screenshotState2);
        setTimeout(() => {
            button.textContent = originalText;
            button.disabled = false;
        }, 2000);

    } catch (error) {
        console.error('分段保存失败:', error);
        const buttons = document.querySelector('.save-buttons');
        buttons.style.visibility = 'visible';
        restoreAfterScreenshot(screenshotState2);
        button.textContent = '保存失败';
        setTimeout(() => {
            button.textContent = originalText;
            button.disabled = false;
        }, 2000);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    window.scrollTo(0, 0);

    // 自动检测宽屏模式
    var savedMode = null;
    try { savedMode = localStorage.getItem('trendradar-wide-mode'); } catch(e) {}
    if (savedMode === '1' || (savedMode === null && window.innerWidth > 768)) {
        document.body.classList.add('wide-mode');
        var btn = document.querySelector('.toggle-wide-btn');
        if (btn) btn.textContent = '⊡';
    }

    // 暗色模式恢复
    var savedDark = null;
    try { savedDark = localStorage.getItem('trendradar-dark-mode'); } catch(e) {}
    if (savedDark === '1') {
        document.body.classList.add('dark-mode');
        var darkBtn = document.querySelector('.toggle-dark-btn');
        if (darkBtn) darkBtn.textContent = '☀';
    }

    // 启用搜索栏
    var searchBar = document.querySelector('.search-bar');
    if (searchBar) searchBar.style.display = 'block';

    // 初始化增强功能
    initTabs();
    initBackToTop();
    initCollapse();
    initStandaloneTabs();

    // 键盘快捷键
    document.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        var helpBtn = document.querySelector('.fab-help');
        switch(e.key) {
            case '?':
                if (helpBtn) {
                    helpBtn.classList.toggle('show-tip');
                    var fabBar = document.querySelector('.fab-bar');
                    if (fabBar) fabBar.classList.add('visible');
                }
                break;
            case 'Escape':
                if (helpBtn) helpBtn.classList.remove('show-tip');
                break;
            case 'w': case 'W': toggleWideMode(); break;
            case 'd': case 'D': toggleDarkMode(); break;
            case '/': e.preventDefault(); var si = document.querySelector('.search-input'); if (si) si.focus(); break;
        }
    });

    // 阅读进度条
    var progressBar = document.querySelector('.reading-progress');
    if (progressBar) {
        window.addEventListener('scroll', function() {
            var h = document.documentElement.scrollHeight - window.innerHeight;
            progressBar.style.width = (h > 0 ? (window.scrollY / h * 100) : 0) + '%';
        });
    }

    // 一键复制：hover 时数字变复制图标
    var copySvg = '<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="5" y="5" width="9" height="9" rx="1.5"/><path d="M5 11H3.5A1.5 1.5 0 012 9.5v-7A1.5 1.5 0 013.5 1h7A1.5 1.5 0 0112 2.5V5"/></svg>';
    var checkSvg = '<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="#22c55e" stroke-width="2"><path d="M3 8.5l3.5 3.5 7-7"/></svg>';
    document.querySelectorAll('.news-item .news-number').forEach(function(numEl) {
        var item = numEl.closest('.news-item');
        var titleEl = item ? item.querySelector('.news-title a') : null;
        if (!titleEl) return;
        var numText = numEl.textContent.trim();
        numEl.innerHTML = '<span class="num-text">' + numText + '</span><span class="copy-icon">' + copySvg + '</span>';
        numEl.title = '点击复制标题和链接';
        numEl.addEventListener('click', function(e) {
            e.stopPropagation();
            var text = titleEl.textContent.trim() + ' ' + titleEl.href;
            navigator.clipboard.writeText(text).then(function() {
                numEl.classList.add('copied');
                numEl.querySelector('.copy-icon').innerHTML = checkSvg;
                setTimeout(function() {
                    numEl.classList.remove('copied');
                    numEl.querySelector('.copy-icon').innerHTML = copySvg;
                }, 1500);
            });
        });
    });



    // Header watermark 鼠标跟随揭示
    (function() {
        var header = document.querySelector('.header');
        var watermark = document.querySelector('.header-watermark');
        if (!header || !watermark) return;

        var radius = 100;

        header.addEventListener('mousemove', function(e) {
            var rect = watermark.getBoundingClientRect();
            var x = e.clientX - rect.left;
            var y = e.clientY - rect.top;
            var maskVal = 'radial-gradient(circle ' + radius + 'px at ' + x + 'px ' + y + 'px, rgba(0,0,0,1) 0%, rgba(0,0,0,0.3) 50%, rgba(0,0,0,0) 100%)';
            watermark.style.webkitMaskImage = maskVal;
            watermark.style.maskImage = maskVal;
            watermark.style.color = 'rgba(255, 255, 255, 0.25)';
        });

        header.addEventListener('mouseleave', function() {
            watermark.style.webkitMaskImage = 'radial-gradient(circle 0px at 50% 50%, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)';
            watermark.style.maskImage = 'radial-gradient(circle 0px at 50% 50%, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)';
            watermark.style.color = 'rgba(255, 255, 255, 0.15)';
        });
    })();
});
