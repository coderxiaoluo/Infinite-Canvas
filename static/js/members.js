(function () {
    'use strict';

    var ROLE_LABELS = {
        editor: '编辑者',
        viewer: '只读',
    };

    var USERNAME_RE = /^[a-zA-Z0-9]{4,80}$/;

    var ICON_BAN = '<svg class="act-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>';
    var ICON_KEY = '<svg class="act-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>';
    var ICON_ROLE = '<svg class="act-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>';
    var ICON_TRASH = '<svg class="act-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';
    var ICON_CHECK = '<svg class="act-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';

    var rowsEl = document.getElementById('member-rows');
    var memberCountEl = document.getElementById('member-count');
    var formError = document.getElementById('form-error');
    var createForm = document.getElementById('create-form');
    var usernameInput = document.getElementById('new-username');
    var passwordInput = document.getElementById('new-password');
    var usernameMsg = document.getElementById('username-msg');
    var passwordMsg = document.getElementById('password-msg');

    var existingUsernames = new Set();
    var membersCache = [];
    var ownerUsername = '';

    /* ---- 弹窗 ---- */

    function openModal(id) {
        var el = document.getElementById(id);
        if (el) el.classList.add('open');
    }

    function closeModal(id) {
        var el = document.getElementById(id);
        if (el) el.classList.remove('open');
    }

    function showConfirm(title, body) {
        return new Promise(function (resolve) {
            var titleEl = document.getElementById('modal-confirm-title');
            var bodyEl = document.getElementById('modal-confirm-body');
            var okBtn = document.getElementById('modal-confirm-ok');
            var cancelBtn = document.getElementById('modal-confirm-cancel');
            if (!titleEl || !bodyEl || !okBtn || !cancelBtn) {
                resolve(window.confirm(body || title));
                return;
            }
            titleEl.textContent = title || '确认';
            bodyEl.textContent = body || '';
            bodyEl.classList.remove('warn');
            openModal('modal-confirm');

            function cleanup(result) {
                closeModal('modal-confirm');
                okBtn.removeEventListener('click', onOk);
                cancelBtn.removeEventListener('click', onCancel);
                resolve(result);
            }
            function onOk() { cleanup(true); }
            function onCancel() { cleanup(false); }
            okBtn.addEventListener('click', onOk);
            cancelBtn.addEventListener('click', onCancel);
        });
    }

    function showWeakPasswordWarning(reason) {
        return new Promise(function (resolve) {
            var bodyEl = document.getElementById('modal-weak-pwd-body');
            var backBtn = document.getElementById('modal-weak-pwd-back');
            var continueBtn = document.getElementById('modal-weak-pwd-continue');
            if (!bodyEl || !backBtn || !continueBtn) {
                resolve(window.confirm(reason + '\n\n仍要继续？'));
                return;
            }
            bodyEl.textContent = reason + ' 建议使用字母与数字组合以提高安全性。';
            openModal('modal-weak-pwd');

            function cleanup(result) {
                closeModal('modal-weak-pwd');
                backBtn.removeEventListener('click', onBack);
                continueBtn.removeEventListener('click', onContinue);
                resolve(result);
            }
            function onBack() { cleanup(false); }
            function onContinue() { cleanup(true); }
            backBtn.addEventListener('click', onBack);
            continueBtn.addEventListener('click', onContinue);
        });
    }

    function showResetPasswordModal(username) {
        return new Promise(function (resolve) {
            var hintEl = document.getElementById('modal-reset-pwd-hint');
            var inputEl = document.getElementById('reset-pwd-input');
            var errorEl = document.getElementById('reset-pwd-error');
            var okBtn = document.getElementById('modal-reset-pwd-ok');
            var cancelBtn = document.getElementById('modal-reset-pwd-cancel');
            if (!inputEl || !okBtn || !cancelBtn) {
                resolve(prompt('输入新密码（至少 6 位）') || null);
                return;
            }
            if (hintEl) hintEl.textContent = '为子账号「' + username + '」设置新密码';
            inputEl.value = '';
            if (errorEl) errorEl.textContent = '';
            openModal('modal-reset-pwd');
            setTimeout(function () { inputEl.focus(); }, 50);

            function cleanup(result) {
                closeModal('modal-reset-pwd');
                okBtn.removeEventListener('click', onOk);
                cancelBtn.removeEventListener('click', onCancel);
                inputEl.removeEventListener('keydown', onKey);
                resolve(result);
            }
            function onOk() {
                var pwd = inputEl.value;
                var check = checkPasswordStrength(pwd);
                if (!check.valid) {
                    if (errorEl) errorEl.textContent = check.message;
                    return;
                }
                if (check.weak) {
                    showWeakPasswordWarning(check.weakReason).then(function (proceed) {
                        if (proceed) cleanup(pwd);
                    });
                    return;
                }
                cleanup(pwd);
            }
            function onCancel() { cleanup(null); }
            function onKey(e) {
                if (e.key === 'Enter') { e.preventDefault(); onOk(); }
                if (e.key === 'Escape') onCancel();
            }
            okBtn.addEventListener('click', onOk);
            cancelBtn.addEventListener('click', onCancel);
            inputEl.addEventListener('keydown', onKey);
        });
    }

    /* ---- 校验 ---- */

    function setError(msg) {
        if (formError) formError.textContent = msg || '';
    }

    function setFieldState(input, msgEl, state, message) {
        if (!input) return;
        input.classList.remove('field-invalid', 'field-valid');
        if (state === 'invalid') input.classList.add('field-invalid');
        if (state === 'valid') input.classList.add('field-valid');
        if (msgEl) {
            msgEl.textContent = message || '';
            msgEl.className = 'field-msg' + (state === 'invalid' ? ' error' : state === 'valid' ? ' ok' : '');
        }
    }

    function validateUsernameFormat(username) {
        if (!username) return { valid: false, message: '请输入账号名' };
        if (username.length < 4) return { valid: false, message: '账号至少 4 位' };
        if (!/^[a-zA-Z0-9]+$/.test(username)) return { valid: false, message: '仅允许字母和数字' };
        if (!USERNAME_RE.test(username)) return { valid: false, message: '账号格式不正确' };
        return { valid: true, message: '' };
    }

    function validateUsernameUnique(username) {
        if (existingUsernames.has(username.toLowerCase())) {
            return { valid: false, message: '该账号名已被使用' };
        }
        return { valid: true, message: '账号名可用' };
    }

    function validateUsername(username) {
        var fmt = validateUsernameFormat(username);
        if (!fmt.valid) return fmt;
        return validateUsernameUnique(username);
    }

    function checkPasswordStrength(password) {
        if (!password || password.length < 6) {
            return { valid: false, message: '密码至少 6 位', weak: false };
        }
        if (/^\d+$/.test(password)) {
            return { valid: true, weak: true, weakReason: '当前密码为纯数字' };
        }
        if (/^[a-zA-Z]+$/.test(password)) {
            return { valid: true, weak: true, weakReason: '当前密码为纯字母' };
        }
        return { valid: true, weak: false };
    }

    function onUsernameInput() {
        var username = usernameInput.value.trim();
        if (!username) {
            setFieldState(usernameInput, usernameMsg, null, '');
            return;
        }
        var fmt = validateUsernameFormat(username);
        if (!fmt.valid) {
            setFieldState(usernameInput, usernameMsg, 'invalid', fmt.message);
            return;
        }
        var uniq = validateUsernameUnique(username);
        setFieldState(usernameInput, usernameMsg, uniq.valid ? 'valid' : 'invalid', uniq.message);
    }

    function onPasswordInput() {
        var password = passwordInput.value;
        if (!password) {
            setFieldState(passwordInput, passwordMsg, null, '');
            return;
        }
        var check = checkPasswordStrength(password);
        if (!check.valid) {
            setFieldState(passwordInput, passwordMsg, 'invalid', check.message);
        } else if (check.weak) {
            setFieldState(passwordInput, passwordMsg, 'invalid', check.weakReason);
        } else {
            setFieldState(passwordInput, passwordMsg, 'valid', '密码强度良好');
        }
    }

    function roleLabel(role) {
        return ROLE_LABELS[role] || role;
    }

    function formatTime(ms) {
        if (!ms) return '—';
        try {
            return new Date(ms).toLocaleString();
        } catch (e) {
            return '—';
        }
    }

    function escapeHtml(text) {
        return String(text || '').replace(/[&<>"']/g, function (c) {
            return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
        });
    }

    async function api(path, options) {
        return window.StudioAuth.apiFetch(path, options || {});
    }

    async function ensureAccess() {
        var result = await window.StudioAuth.initPage({ redirect: true, next: '/members' });
        if (!result.ok) throw new Error('未登录');
        var me = await window.StudioAuth.fetchMe();
        if (!me.is_owner) {
            alert('管理后台仅主账号可访问');
            location.href = '/';
            throw new Error('forbidden');
        }
        if (me.user && me.user.username) {
            ownerUsername = me.user.username.toLowerCase();
        }
        return me;
    }

    function rebuildUsernameSet(members) {
        membersCache = members || [];
        existingUsernames.clear();
        if (ownerUsername) existingUsernames.add(ownerUsername);
        membersCache.forEach(function (m) {
            if (m.username) existingUsernames.add(m.username.toLowerCase());
        });
    }

    async function loadMembers() {
        var res = await api('/api/tenant/members');
        if (!res.ok) {
            var err = await res.json().catch(function () { return {}; });
            throw new Error(err.detail || '加载失败');
        }
        var data = await res.json();
        rebuildUsernameSet(data.members || []);
        renderRows(data.members || []);
    }

    function updateMemberCount(count) {
        if (!memberCountEl) return;
        if (count > 0) {
            memberCountEl.textContent = String(count);
            memberCountEl.hidden = false;
        } else {
            memberCountEl.hidden = true;
        }
    }

    function renderRows(members) {
        if (!rowsEl) return;
        updateMemberCount(members.length);
        if (!members.length) {
            rowsEl.innerHTML = '<tr class="empty-row"><td colspan="5">暂无子账号</td></tr>';
            return;
        }
        rowsEl.innerHTML = members.map(function (m) {
            var disabled = m.status !== 'active';
            var toggleLabel = disabled ? '启用' : '禁用';
            var toggleIcon = disabled ? ICON_CHECK : ICON_BAN;
            var toggleClass = disabled ? 'act-btn' : 'act-btn act-danger';
            var actions = [
                '<button class="' + toggleClass + '" data-action="toggle" data-id="' + m.id + '" data-username="' + escapeHtml(m.username) + '" data-status="' + (disabled ? 'active' : 'disabled') + '">' + toggleIcon + toggleLabel + '</button>',
                '<button class="act-btn" data-action="reset" data-id="' + m.id + '" data-username="' + escapeHtml(m.username) + '">' + ICON_KEY + '密码</button>',
                '<button class="act-btn" data-action="role" data-id="' + m.id + '" data-role="' + m.role + '">' + ICON_ROLE + '权限</button>',
                '<button class="act-btn act-danger" data-action="delete" data-id="' + m.id + '" data-username="' + escapeHtml(m.username) + '">' + ICON_TRASH + '删除</button>',
            ];
            return '<tr>' +
                '<td class="col-username">' + escapeHtml(m.username) + '</td>' +
                '<td><span class="role-badge">' + roleLabel(m.role) + '</span></td>' +
                '<td><span class="status-badge ' + (disabled ? 'disabled' : 'active') + '">' + (disabled ? '已禁用' : '已启用') + '</span></td>' +
                '<td class="col-time">' + formatTime(m.last_login_at) + '</td>' +
                '<td><div class="actions">' + actions.join('') + '</div></td>' +
                '</tr>';
        }).join('');
    }

    rowsEl.addEventListener('click', async function (event) {
        var btn = event.target.closest('[data-action]');
        if (!btn) return;
        var id = btn.getAttribute('data-id');
        var username = btn.getAttribute('data-username') || '';
        var action = btn.getAttribute('data-action');
        try {
            if (action === 'toggle') {
                var status = btn.getAttribute('data-status');
                var isDisable = status === 'disabled';
                var ok = await showConfirm(
                    isDisable ? '禁用子账号' : '启用子账号',
                    isDisable
                        ? '确定禁用子账号「' + username + '」？禁用后该账号将无法登录。'
                        : '确定启用子账号「' + username + '」？'
                );
                if (!ok) return;
                var res = await api('/api/tenant/members/' + id, {
                    method: 'PATCH',
                    body: JSON.stringify({ status: status }),
                });
                if (!res.ok) throw new Error((await res.json()).detail || '操作失败');
            } else if (action === 'delete') {
                var confirmed = await showConfirm(
                    '删除子账号',
                    '确定删除子账号「' + username + '」？其画布与数据将无法以此账号登录访问，此操作不可撤销。'
                );
                if (!confirmed) return;
                var del = await api('/api/tenant/members/' + id, { method: 'DELETE' });
                if (!del.ok) throw new Error((await del.json()).detail || '删除失败');
            } else if (action === 'reset') {
                var pwd = await showResetPasswordModal(username);
                if (!pwd) return;
                var reset = await api('/api/tenant/members/' + id + '/reset-password', {
                    method: 'POST',
                    body: JSON.stringify({ password: pwd }),
                });
                if (!reset.ok) throw new Error((await reset.json()).detail || '修改失败');
                await showConfirm('修改成功', '子账号「' + username + '」的密码已更新。');
            } else if (action === 'role') {
                var current = btn.getAttribute('data-role');
                var next = prompt('输入权限：editor（编辑）或 viewer（只读）', current || 'editor');
                if (!next) return;
                next = next.trim().toLowerCase();
                if (['editor', 'viewer'].indexOf(next) === -1) {
                    alert('无效权限');
                    return;
                }
                var patch = await api('/api/tenant/members/' + id, {
                    method: 'PATCH',
                    body: JSON.stringify({ role: next }),
                });
                if (!patch.ok) throw new Error((await patch.json()).detail || '修改失败');
            }
            await loadMembers();
        } catch (e) {
            alert(e.message || '操作失败');
        }
    });

    createForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        setError('');
        var username = usernameInput.value.trim();
        var password = passwordInput.value;
        var role = document.getElementById('new-role').value;

        var userCheck = validateUsername(username);
        if (!userCheck.valid) {
            setFieldState(usernameInput, usernameMsg, 'invalid', userCheck.message);
            setError(userCheck.message);
            usernameInput.focus();
            return;
        }

        var pwdCheck = checkPasswordStrength(password);
        if (!pwdCheck.valid) {
            setFieldState(passwordInput, passwordMsg, 'invalid', pwdCheck.message);
            setError(pwdCheck.message);
            passwordInput.focus();
            return;
        }

        if (pwdCheck.weak) {
            var proceedWeak = await showWeakPasswordWarning(pwdCheck.weakReason);
            if (!proceedWeak) {
                passwordInput.focus();
                return;
            }
        }

        var roleText = roleLabel(role);
        var confirmed = await showConfirm(
            '创建子账号',
            '确定创建子账号「' + username + '」（权限：' + roleText + '）？'
        );
        if (!confirmed) return;

        try {
            var res = await api('/api/tenant/members', {
                method: 'POST',
                body: JSON.stringify({ username: username, password: password, role: role }),
            });
            var data = await res.json().catch(function () { return {}; });
            if (!res.ok) throw new Error(data.detail || '创建失败');
            createForm.reset();
            setFieldState(usernameInput, usernameMsg, null, '');
            setFieldState(passwordInput, passwordMsg, null, '');
            existingUsernames.add(username.toLowerCase());
            await loadMembers();
        } catch (e) {
            if (e.message && e.message.indexOf('已存在') !== -1) {
                setFieldState(usernameInput, usernameMsg, 'invalid', '该账号名已被使用');
            }
            setError(e.message || '创建失败');
        }
    });

    if (usernameInput) {
        usernameInput.addEventListener('input', onUsernameInput);
        usernameInput.addEventListener('blur', onUsernameInput);
    }
    if (passwordInput) {
        passwordInput.addEventListener('input', onPasswordInput);
        passwordInput.addEventListener('blur', onPasswordInput);
    }

    document.addEventListener('DOMContentLoaded', async function () {
        if (!window.StudioAuth) return;
        try {
            await ensureAccess();
            await loadMembers();
        } catch (e) {
            if (rowsEl) rowsEl.innerHTML = '<tr class="empty-row"><td colspan="5">无法加载子账号列表</td></tr>';
        }
    });
})();
