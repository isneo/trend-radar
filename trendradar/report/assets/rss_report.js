async function saveAsImage() {
    const button = event.target;
    const originalText = button.textContent;

    try {
        button.textContent = '生成中...';
        button.disabled = true;
        window.scrollTo(0, 0);

        await new Promise(resolve => setTimeout(resolve, 200));

        const buttons = document.querySelector('.save-buttons');
        buttons.style.visibility = 'hidden';

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

        const link = document.createElement('a');
        const now = new Date();
        const filename = `TrendRadar_RSS订阅_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}.png`;

        link.download = filename;
        link.href = canvas.toDataURL('image/png', 1.0);

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
        button.textContent = '保存失败';
        setTimeout(() => {
            button.textContent = originalText;
            button.disabled = false;
        }, 2000);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    window.scrollTo(0, 0);
});
