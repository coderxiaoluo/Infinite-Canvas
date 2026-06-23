(function () {

    'use strict';



    var ACCESS_KEY = 'ic_access_token';

    var USER_KEY = 'ic_user_cache';

    var LOGIN_PATH = '/login';

    var statusCache = null;

    var refreshPromise = null;

    var nativeFetch = window.fetch.bind(window);

    var openMenuEl = null;

    var menuDocBound = false;



    var AVATAR_COLORS = ['#6366f1', '#8b5cf6', '#a855f7', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#14b8a6'];



    var ICONS = {

        admin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',

        settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',

        logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',

        chevron: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>',

    };



    function getAccessToken() {

        try {

            return localStorage.getItem(ACCESS_KEY) || '';

        } catch (e) {

            return '';

        }

    }



    function setAccessToken(token) {

        try {

            if (token) localStorage.setItem(ACCESS_KEY, token);

            else localStorage.removeItem(ACCESS_KEY);

        } catch (e) {}

    }



    function getCachedUser() {

        try {

            var raw = localStorage.getItem(USER_KEY);

            return raw ? JSON.parse(raw) : null;

        } catch (e) {

            return null;

        }

    }



    function setCachedUser(user) {

        try {

            if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));

            else localStorage.removeItem(USER_KEY);

        } catch (e) {}

    }



    function loginUrl(next) {

        var target = next || (window.location.pathname + window.location.search);

        if (!target || target === LOGIN_PATH || target.indexOf('/static/login.html') === 0) target = '/';

        return LOGIN_PATH + '?next=' + encodeURIComponent(target);

    }



    function redirectToLogin(next) {

        var url = loginUrl(next);

        if (window.top && window.top !== window.self) {

            window.top.location.href = url;

        } else {

            window.location.href = url;

        }

    }



    async function getStatus(force) {

        if (!force && statusCache) return statusCache;

        var res = await nativeFetch('/api/auth/status', { cache: 'no-store' });

        statusCache = await res.json();

        return statusCache;

    }



    function authHeaders(extra) {

        var headers = Object.assign({}, extra || {});

        var token = getAccessToken();

        if (token) headers.Authorization = 'Bearer ' + token;

        return headers;

    }



    async function refreshAccessToken() {

        if (refreshPromise) return refreshPromise;

        refreshPromise = nativeFetch('/api/auth/refresh', {

            method: 'POST',

            headers: { 'Content-Type': 'application/json' },

            credentials: 'same-origin',

            body: '{}',

        }).then(async function (res) {

            if (!res.ok) throw new Error('refresh failed');

            var data = await res.json();

            setAccessToken(data.access_token || '');

            if (data.user) setCachedUser(data.user);

            return data.access_token || '';

        }).finally(function () {

            refreshPromise = null;

        });

        return refreshPromise;

    }



    async function apiFetch(url, options) {

        options = options || {};

        var opts = Object.assign({}, options);

        var headers = authHeaders(options.headers || {});

        if (!(options.body instanceof FormData) && !headers['Content-Type'] && !(options.body instanceof Blob)) {

            headers['Content-Type'] = headers['Content-Type'] || 'application/json';

        }

        opts.headers = headers;

        opts.credentials = options.credentials || 'same-origin';



        var res = await nativeFetch(url, opts);

        if (res.status !== 401) return res;



        var status = await getStatus(false);

        if (!status.auth_required) return res;



        try {

            await refreshAccessToken();

        } catch (e) {

            setAccessToken('');

            setCachedUser(null);

            redirectToLogin();

            return res;

        }



        opts.headers = authHeaders(options.headers || {});

        return nativeFetch(url, opts);

    }



    function patchFetch() {

        if (window.__icAuthFetchPatched) return;

        window.__icAuthFetchPatched = true;

        window.fetch = function (url, options) {

            var path = typeof url === 'string' ? url : (url && url.url) || '';

            if (path.indexOf('/api/') === -1) return nativeFetch(url, options);

            return apiFetch(path, options);

        };

    }



    async function login(username, password) {

        var res = await nativeFetch('/api/auth/login', {

            method: 'POST',

            headers: { 'Content-Type': 'application/json' },

            credentials: 'same-origin',

            body: JSON.stringify({ username: username, password: password }),

        });

        var data = await res.json().catch(function () { return {}; });

        if (!res.ok) throw new Error(data.detail || '登录失败');

        setAccessToken(data.access_token || '');

        if (data.user) setCachedUser(data.user);

        return data;

    }



    async function register(payload) {

        var res = await nativeFetch('/api/auth/register', {

            method: 'POST',

            headers: { 'Content-Type': 'application/json' },

            credentials: 'same-origin',

            body: JSON.stringify({

                username: payload.username || payload.email || '',

                password: payload.password || '',

            }),

        });

        var data = await res.json().catch(function () { return {}; });

        if (!res.ok) throw new Error(data.detail || '注册失败');

        setAccessToken(data.access_token || '');

        if (data.user) setCachedUser(data.user);

        return data;

    }



    async function logout() {

        closeUserMenu();

        try {

            await nativeFetch('/api/auth/logout', {

                method: 'POST',

                headers: authHeaders({ 'Content-Type': 'application/json' }),

                credentials: 'same-origin',

                body: '{}',

            });

        } catch (e) {}

        setAccessToken('');

        setCachedUser(null);

        statusCache = null;

        redirectToLogin('/');

    }



    async function fetchMe() {

        var res = await apiFetch('/api/auth/me');

        if (!res.ok) throw new Error('me failed');

        return res.json();

    }



    async function ensureAuth(options) {

        options = options || {};

        var status = await getStatus(false);

        if (!status.auth_required) return { ok: true, required: false, user: null };



        if (!getAccessToken()) {

            if (options.redirect !== false) redirectToLogin(options.next);

            return { ok: false, required: true, user: null };

        }



        try {

            var me = await fetchMe();

            if (me.user) setCachedUser(me.user);

            return { ok: true, required: true, user: me.user || getCachedUser(), me: me };

        } catch (e) {

            setAccessToken('');

            setCachedUser(null);

            if (options.redirect !== false) redirectToLogin(options.next);

            return { ok: false, required: true, user: null };

        }

    }



    async function initPage(options) {

        patchFetch();

        options = options || {};

        var result = await ensureAuth(options);

        if (result.ok || !result.required) {

            await initUserMenus();

        }

        if (typeof options.onReady === 'function') {

            options.onReady(result);

        }

        return result;

    }



    function ROLE_LABEL(user) {

        if (!user) return '';

        if (user.account_type === 'owner' || user.role === 'owner') return '主账号';

        var map = { editor: '编辑者', viewer: '只读' };

        return map[user.role] || '子账号';

    }



    function avatarInitial(name) {

        var s = String(name || 'U').trim();

        if (!s) return 'U';

        return s.slice(0, 1).toUpperCase();

    }



    function avatarColor(name) {

        var s = String(name || '');

        var h = 0;

        for (var i = 0; i < s.length; i++) h = (h + s.charCodeAt(i)) % AVATAR_COLORS.length;

        return AVATAR_COLORS[h];

    }



    function closeUserMenu() {

        if (!openMenuEl) return;

        openMenuEl.classList.remove('is-open');

        openMenuEl = null;

    }



    function bindMenuDocumentEvents() {

        if (menuDocBound) return;

        menuDocBound = true;

        document.addEventListener('click', function (e) {

            if (!openMenuEl) return;

            if (openMenuEl.contains(e.target)) return;

            closeUserMenu();

        });

        document.addEventListener('keydown', function (e) {

            if (e.key === 'Escape') closeUserMenu();

        });

    }



    function createMenuItem(label, iconKey, onClick, extraClass) {

        var btn = document.createElement('button');

        btn.type = 'button';

        btn.className = 'auth-user-menu-item' + (extraClass ? ' ' + extraClass : '');

        btn.innerHTML = (ICONS[iconKey] || '') + '<span>' + label + '</span>';

        btn.addEventListener('click', function (e) {

            e.stopPropagation();

            closeUserMenu();

            onClick();

        });

        return btn;

    }



    function navigateTo(url) {

        if (window.top && window.top !== window.self) {

            window.top.location.href = url;

        } else {

            window.location.href = url;

        }

    }



    function openSettings() {

        if (window.top && window.top !== window.self && typeof window.top.switchUI === 'function') {

            window.top.switchUI(null, 'api-settings');

            return;

        }

        navigateTo('/static/api-settings.html');

    }



    function userIsOwner(user) {
        if (!user) return false;
        return user.account_type === 'owner' || user.role === 'owner';
    }

    function resolveAuthPayload(payload) {
        var user = (payload && payload.user) || getCachedUser();
        var isOwner = payload && payload.is_owner === true;
        if (!isOwner && userIsOwner(user)) isOwner = true;
        return { user: user, is_owner: isOwner };
    }

    function renderUserMenuMount(mount, payload) {
        if (!mount || mount.__authMenuRendered) return;
        var resolved = resolveAuthPayload(payload);
        var user = resolved.user;
        if (!user) return;

        var compact = mount.getAttribute('data-compact') === 'true' || mount.classList.contains('compact');
        var placementTop = mount.getAttribute('data-menu-placement') === 'top';
        var username = user.username || user.display_name || '用户';
        var isOwner = resolved.is_owner;



        mount.innerHTML = '';

        mount.__authMenuRendered = true;



        var root = document.createElement('div');

        root.className = 'auth-user-menu is-visible' + (compact ? ' compact' : '') + (placementTop ? ' placement-top' : '');



        var trigger = document.createElement('button');

        trigger.type = 'button';

        trigger.className = 'auth-user-menu-trigger';

        trigger.setAttribute('aria-haspopup', 'true');

        trigger.setAttribute('aria-expanded', 'false');

        trigger.innerHTML =

            '<span class="auth-user-menu-avatar" style="background:' + avatarColor(username) + '">' + escapeHtml(avatarInitial(username)) + '</span>' +

            '<span class="auth-user-menu-name">' + escapeHtml(username) + '</span>' +

            '<span class="auth-user-menu-chevron">' + ICONS.chevron + '</span>';



        var dropdown = document.createElement('div');

        dropdown.className = 'auth-user-menu-dropdown';

        dropdown.setAttribute('role', 'menu');



        var head = document.createElement('div');

        head.className = 'auth-user-menu-head';

        head.innerHTML =

            '<div class="auth-user-menu-head-name">' + escapeHtml(username) + '</div>' +

            '<div class="auth-user-menu-head-role">' + escapeHtml(ROLE_LABEL(user)) + '</div>';

        dropdown.appendChild(head);



        if (isOwner) {

            dropdown.appendChild(createMenuItem('管理后台', 'admin', function () {

                navigateTo('/members');

            }));

            dropdown.appendChild(createMenuItem('设置', 'settings', openSettings));

            var divider = document.createElement('div');

            divider.className = 'auth-user-menu-divider';

            dropdown.appendChild(divider);

        }



        dropdown.appendChild(createMenuItem('退出登录', 'logout', logout, 'is-danger'));



        trigger.addEventListener('click', function (e) {

            e.stopPropagation();

            var willOpen = !root.classList.contains('is-open');

            closeUserMenu();

            if (willOpen) {

                root.classList.add('is-open');

                trigger.setAttribute('aria-expanded', 'true');

                openMenuEl = root;

            }

        });



        root.appendChild(trigger);

        root.appendChild(dropdown);

        mount.appendChild(root);

    }



    function escapeHtml(text) {

        return String(text || '').replace(/[&<>"']/g, function (c) {

            return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];

        });

    }



    async function initUserMenus() {

        bindMenuDocumentEvents();

        var mounts = document.querySelectorAll('[data-auth-user-menu]');

        if (!mounts.length) return;



        var status = await getStatus(false);

        if (!status.auth_required) {
            mounts.forEach(function (mount) {
                mount.classList.remove('is-auth-ready');
                mount.style.display = 'none';
            });
            return;
        }



        var payload;

        try {

            payload = await fetchMe();

            if (payload.user) setCachedUser(payload.user);

        } catch (e) {
            var cached = getCachedUser();
            payload = { user: cached, is_owner: userIsOwner(cached) };
        }



        if (!payload.user && !getCachedUser()) return;



        mounts.forEach(function (mount) {
            mount.classList.add('is-auth-ready');
            mount.style.display = '';
            renderUserMenuMount(mount, payload);
        });

    }



    function renderUserBadge(containerId) {

        var box = document.getElementById(containerId);

        if (!box) return;

        if (!box.hasAttribute('data-auth-user-menu')) {

            box.setAttribute('data-auth-user-menu', '');

        }

        initUserMenus();

    }



    async function ensureOwnerAccess(options) {

        options = options || {};

        var result = await ensureAuth({

            redirect: options.redirect !== false,

            next: options.next || (window.location.pathname + window.location.search),

        });

        if (!result.ok) return result;

        var status = await getStatus(false);

        if (!status.auth_required) return { ok: true, is_owner: true, user: result.user, required: false };

        var me;

        try { me = await fetchMe(); } catch (e) { me = {}; }

        var resolved = resolveAuthPayload(me);

        if (resolved.is_owner) return { ok: true, is_owner: true, user: resolved.user || result.user, required: true };

        var msg = options.message || '当前账号无权访问此页面';

        var fallback = options.fallback || '/';

        if (options.redirect !== false) {

            try {

                if (window.top && window.top !== window.self) {

                    window.top.postMessage({ type: 'studio-forbidden-page', page: window.location.pathname }, '*');

                }

            } catch (e) {}

            try {

                if (window.top && window.top !== window.self) window.top.location.href = fallback;

                else { alert(msg); window.location.href = fallback; }

            } catch (e2) {

                alert(msg);

                window.location.href = fallback;

            }

        } else if (options.alert !== false) {

            alert(msg);

        }

        return { ok: false, forbidden: true, is_owner: false, user: resolved.user, required: true };

    }



    var OWNER_ONLY_PAGE_IDS = ['zimage', 'enhance', 'klein', 'angle', 'api-settings', 'comfyui-settings'];



    window.StudioAuth = {

        getAccessToken: getAccessToken,

        getCachedUser: getCachedUser,

        getStatus: getStatus,

        ensureAuth: ensureAuth,

        ensureOwnerAccess: ensureOwnerAccess,

        initPage: initPage,

        initUserMenus: initUserMenus,

        login: login,

        register: register,

        logout: logout,

        fetchMe: fetchMe,

        apiFetch: apiFetch,

        redirectToLogin: redirectToLogin,

        renderUserBadge: renderUserBadge,

        patchFetch: patchFetch,

        userIsOwner: userIsOwner,

        OWNER_ONLY_PAGE_IDS: OWNER_ONLY_PAGE_IDS,

    };



    patchFetch();

})();

