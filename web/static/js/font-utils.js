/**
 * font-utils.js  –  전역 폰트 크기 조절 유틸리티
 * 모든 페이지 공통 사용 / localStorage 키: 'fontSize' 통일
 */
(function () {
    const FONT_SIZES  = ['xs', 'small', 'normal', 'medium', 'large', 'xl', 'xxl'];
    const STORAGE_KEY = 'fontSize';
    let currentFontIndex = 2;   // 기본값: normal

    function setFontSize(size) {
        document.body.className = document.body.className
            .replace(/\bfont-\w+\b/g, '').trim();
        if (size !== 'normal') {
            document.body.classList.add('font-' + size);
        }
        currentFontIndex = FONT_SIZES.indexOf(size);
        if (currentFontIndex === -1) currentFontIndex = 2;
        localStorage.setItem(STORAGE_KEY, size);
        console.log('[font-utils] 폰트 크기:', size,
                    '(' + (currentFontIndex + 1) + '/' + FONT_SIZES.length + ')');
    }

    function increaseFontSize() {
        currentFontIndex = Math.min(currentFontIndex + 1, FONT_SIZES.length - 1);
        setFontSize(FONT_SIZES[currentFontIndex]);
    }

    function decreaseFontSize() {
        currentFontIndex = Math.max(currentFontIndex - 1, 0);
        setFontSize(FONT_SIZES[currentFontIndex]);
    }

    function resetFontSize() { setFontSize('normal'); }

    // 페이지 로드 시 저장된 폰트 크기 복원
    document.addEventListener('DOMContentLoaded', function () {
        var saved = localStorage.getItem(STORAGE_KEY) || 'normal';
        setFontSize(saved);
    });

    // 전역 노출 (HTML onclick="..." 에서 호출 가능)
    window.setFontSize      = setFontSize;
    window.increaseFontSize = increaseFontSize;
    window.decreaseFontSize = decreaseFontSize;
    window.resetFontSize    = resetFontSize;
})();
