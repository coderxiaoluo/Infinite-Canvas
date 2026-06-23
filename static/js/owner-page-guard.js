(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', function () {
        if (!window.StudioAuth || !window.StudioAuth.ensureOwnerAccess) return;
        window.StudioAuth.ensureOwnerAccess({
            redirect: true,
            fallback: '/',
            message: '当前账号无权访问此页面，已跳转到首页。',
        });
    });
})();
