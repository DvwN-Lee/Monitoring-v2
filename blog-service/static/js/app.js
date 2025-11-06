document.addEventListener('DOMContentLoaded', () => {
    const mainContent = document.getElementById('main-content');

    // 전역 상태
    let currentPage = 1;
    let currentCategory = '';
    let categoryCounts = { all: 0, 'tech-stack': 0, 'troubleshooting': 0, 'test': 0 };
    const postsPerPage = 5;

    // JWT helpers
    const getToken = () => sessionStorage.getItem('authToken') || '';
    const parseJwt = (t) => {
        try {
            const base = t.split('.')[1];
            const b = atob(base.replace(/-/g, '+').replace(/_/g, '/'));
            return JSON.parse(b);
        } catch { return null; }
    };
    const getUsernameFromToken = () => {
        const p = parseJwt(getToken());
        return (p && p.username) ? p.username : '';
    };
    const authHeader = () => ({ 'Authorization': `Bearer ${getToken()}` });

    // 템플릿 렌더링
    const renderTemplate = (templateId) => {
        const template = document.getElementById(templateId);
        if (template) {
            mainContent.innerHTML = '';
            mainContent.appendChild(template.content.cloneNode(true));
        }
    };

    // 라우터
    const routes = {
        '/': loadPostList,
        '/posts/new': showPostForm,
        '/posts/:id': showPostDetail,
        '/posts/:id/edit': showPostForm
    };

    const router = () => {
        const path = window.location.hash.slice(1) || '/';

        if (path === '/') {
            routes['/']();
        } else if (path === '/posts/new') {
            routes['/posts/new']('create');
        } else if (path.match(/^\/posts\/\d+$/)) {
            const id = path.split('/')[2];
            routes['/posts/:id'](id);
        } else if (path.match(/^\/posts\/\d+\/edit$/)) {
            const id = path.split('/')[2];
            routes['/posts/:id/edit']('edit', id);
        }

        updateAuthStatus();
    };

    // 인증 UI 업데이트
    const updateAuthStatus = () => {
        const token = getToken();
        const authStatus = document.getElementById('auth-status');

        if (token) {
            authStatus.innerHTML = `
                <button class="btn btn-outline" id="write-btn">글쓰기</button>
                <button class="btn btn-primary" id="logout-btn">로그아웃</button>
            `;
            document.getElementById('write-btn')?.addEventListener('click', () => {
                window.location.hash = '/posts/new';
            });
            document.getElementById('logout-btn')?.addEventListener('click', logout);
        } else {
            authStatus.innerHTML = '<button class="btn btn-primary" id="login-btn">로그인</button>';
            document.getElementById('login-btn')?.addEventListener('click', showLoginModal);
        }
    };

    // 모달 관리
    const showLoginModal = () => {
        closeAllModals();
        document.getElementById('login-modal').classList.add('active');
    };

    const showSignupModal = () => {
        closeAllModals();
        document.getElementById('signup-modal').classList.add('active');
    };

    const closeAllModals = () => {
        document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
    };

    // 모달 이벤트 리스너 설정
    document.getElementById('close-login')?.addEventListener('click', closeAllModals);
    document.getElementById('close-signup')?.addEventListener('click', closeAllModals);
    document.getElementById('go-to-signup')?.addEventListener('click', showSignupModal);
    document.getElementById('go-to-login')?.addEventListener('click', showLoginModal);

    // 모달 외부 클릭 시 닫기
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            closeAllModals();
        }
    });

    // 로그인 처리
    document.getElementById('login-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        const errorEl = document.getElementById('login-error');

        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            if (res.ok) {
                sessionStorage.setItem('authToken', data.token);
                closeAllModals();
                updateAuthStatus();
                window.location.hash = '/';
            } else {
                errorEl.textContent = data.error || '로그인 실패';
            }
        } catch (err) {
            errorEl.textContent = '서버와 통신할 수 없습니다.';
        }
    });

    // 회원가입 처리
    document.getElementById('signup-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('signup-username').value;
        const email = document.getElementById('signup-email').value;
        const password = document.getElementById('signup-password').value;
        const errorEl = document.getElementById('signup-error');

        try {
            const res = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password })
            });
            const data = await res.json();
            if (res.ok) {
                alert('회원가입 성공! 로그인 페이지로 이동합니다.');
                showLoginModal();
            } else {
                errorEl.textContent = data.detail || data.error || '회원가입 실패';
            }
        } catch (err) {
            errorEl.textContent = '서버와 통신할 수 없습니다.';
        }
    });

    // 로그아웃
    const logout = () => {
        sessionStorage.removeItem('authToken');
        updateAuthStatus();
        window.location.hash = '/';
        alert('로그아웃 되었습니다.');
    };

    // 카테고리 카운트 가져오기
    const loadCategoryCounts = async () => {
        try {
            const res = await fetch('/api/categories');
            const cats = await res.json();
            categoryCounts.all = cats.reduce((sum, c) => sum + c.post_count, 0);
            cats.forEach(c => {
                categoryCounts[c.slug] = c.post_count;
            });
            updateCategoryCountsUI();
        } catch (err) {
            console.error('카테고리 카운트 로드 실패:', err);
        }
    };

    const updateCategoryCountsUI = () => {
        document.getElementById('count-all')?.innerText = `(${categoryCounts.all})`;
        document.getElementById('count-tech-stack')?.innerText = `(${categoryCounts['tech-stack']})`;
        document.getElementById('count-troubleshooting')?.innerText = `(${categoryCounts['troubleshooting']})`;
        document.getElementById('count-test')?.innerText = `(${categoryCounts['test']})`;
    };

    // 게시물 목록 로드
    const loadPostList = async () => {
        renderTemplate('post-list-template');
        await loadCategoryCounts();
        await loadPosts();
        setupCategoryTabs();
    };

    const setupCategoryTabs = () => {
        document.querySelectorAll('.category-tab').forEach(tab => {
            tab.addEventListener('click', async () => {
                document.querySelectorAll('.category-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentCategory = tab.getAttribute('data-category') || '';
                currentPage = 1;
                await loadPosts();
            });
        });
    };

    const loadPosts = async () => {
        try {
            const url = currentCategory ? `/api/posts?category=${currentCategory}` : '/api/posts';
            const res = await fetch(url);
            const posts = await res.json();
            renderPosts(posts);
        } catch (err) {
            console.error('게시물 로드 실패:', err);
            document.getElementById('posts-container').innerHTML = '<p>게시물을 불러오는 데 실패했습니다.</p>';
        }
    };

    const renderPosts = (allPosts) => {
        const container = document.getElementById('posts-container');
        const start = (currentPage - 1) * postsPerPage;
        const end = start + postsPerPage;
        const posts = allPosts.slice(start, end);

        container.innerHTML = '';
        if (posts.length === 0) {
            container.innerHTML = '<p style="text-align:center;color:#777;padding:40px;">게시물이 없습니다.</p>';
            renderPagination(0);
            return;
        }

        posts.forEach(post => {
            const li = document.createElement('li');
            li.className = 'post-list-item';
            li.onclick = () => { window.location.hash = `/posts/${post.id}`; };
            li.innerHTML = `
                <div class="post-list-header">
                    <div class="post-title">
                        ${post.title}
                        <span class="category-badge ${post.category.slug}">${post.category.name}</span>
                    </div>
                    <span class="post-author">by ${post.author}</span>
                </div>
                <div class="post-excerpt">${(post.excerpt || '').replace(/</g, '&lt;')}</div>
            `;
            container.appendChild(li);
        });

        renderPagination(allPosts.length);
    };

    const renderPagination = (totalPosts) => {
        const totalPages = Math.ceil(totalPosts / postsPerPage);
        const pageNumbersContainer = document.getElementById('page-numbers');
        pageNumbersContainer.innerHTML = '';

        const prevBtn = document.getElementById('prev-btn');
        prevBtn.disabled = currentPage === 1;
        prevBtn.onclick = () => { if (currentPage > 1) { currentPage--; loadPosts(); } };

        const startPage = Math.floor((currentPage - 1) / 10) * 10 + 1;
        const endPage = Math.min(startPage + 9, totalPages);

        for (let i = startPage; i <= endPage; i++) {
            const btn = document.createElement('button');
            btn.className = `page-number ${i === currentPage ? 'active' : ''}`;
            btn.textContent = i;
            btn.onclick = () => { currentPage = i; loadPosts(); };
            pageNumbersContainer.appendChild(btn);
        }

        const nextBtn = document.getElementById('next-btn');
        nextBtn.disabled = currentPage >= totalPages;
        nextBtn.onclick = () => { if (currentPage < totalPages) { currentPage++; loadPosts(); } };
    };

    // 게시물 상세
    const showPostDetail = async (id) => {
        renderTemplate('post-detail-template');
        try {
            const res = await fetch(`/api/posts/${id}`);
            const post = await res.json();

            document.getElementById('detail-title').innerHTML = `${post.title} <span class="category-badge ${post.category.slug}">${post.category.name}</span>`;
            document.getElementById('detail-category').innerHTML = '';
            document.getElementById('detail-author').textContent = `작성자: ${post.author}`;
            document.getElementById('detail-content').innerHTML = post.content.replace(/\n/g, '<br>');

            document.getElementById('back-btn').onclick = () => { window.location.hash = '/'; };

            const canEdit = getToken() && getUsernameFromToken() === post.author;
            if (canEdit) {
                document.getElementById('edit-btn').classList.remove('hidden');
                document.getElementById('delete-btn').classList.remove('hidden');
                document.getElementById('edit-btn').onclick = () => { window.location.hash = `/posts/${id}/edit`; };
                document.getElementById('delete-btn').onclick = async () => {
                    if (!confirm('삭제하시겠습니까?')) return;
                    const res = await fetch(`/api/posts/${id}`, { method: 'DELETE', headers: authHeader() });
                    if (res.status === 204) { alert('삭제되었습니다.'); window.location.hash = '/'; }
                    else { alert('삭제 실패'); }
                };
            }
        } catch (err) {
            console.error('게시물 상세 로드 실패:', err);
            mainContent.innerHTML = '<div class="view-container"><p>게시물을 불러올 수 없습니다.</p></div>';
        }
    };

    // 게시물 작성/수정 폼
    const showPostForm = async (mode, id) => {
        if (!getToken()) {
            alert('로그인이 필요합니다.');
            showLoginModal();
            return;
        }

        renderTemplate('post-form-template');
        const formTitle = document.getElementById('form-title');
        const titleInput = document.getElementById('post-title');
        const contentInput = document.getElementById('post-content');
        const errorEl = document.getElementById('post-error');

        if (mode === 'edit') {
            formTitle.textContent = '글 수정';
            try {
                const res = await fetch(`/api/posts/${id}`);
                const post = await res.json();
                if (getUsernameFromToken() !== post.author) {
                    alert('작성자만 수정할 수 있습니다.');
                    window.location.hash = `/posts/${id}`;
                    return;
                }
                titleInput.value = post.title;
                contentInput.value = post.content;
                document.querySelector(`input[name="category"][value="${post.category.id}"]`).checked = true;
            } catch (err) {
                errorEl.textContent = '게시물을 불러오지 못했습니다.';
            }
        } else {
            formTitle.textContent = '글 작성';
        }

        document.getElementById('cancel-btn').onclick = () => { window.history.back(); };

        document.getElementById('post-form').onsubmit = async (e) => {
            e.preventDefault();
            errorEl.textContent = '';

            const category = document.querySelector('input[name="category"]:checked');
            if (!category) { errorEl.textContent = '카테고리를 선택하세요.'; return; }

            const payload = {
                title: titleInput.value.trim(),
                content: contentInput.value.trim(),
                category_id: parseInt(category.value)
            };

            if (!payload.title || !payload.content) {
                errorEl.textContent = '제목/내용을 입력하세요.';
                return;
            }

            try {
                const url = mode === 'edit' ? `/api/posts/${id}` : '/api/posts';
                const method = mode === 'edit' ? 'PATCH' : 'POST';
                const res = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json', ...authHeader() },
                    body: JSON.stringify(payload)
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    errorEl.textContent = data.detail || data.error || '저장 실패';
                    return;
                }
                const postId = mode === 'edit' ? id : data.id;
                window.location.hash = `/posts/${postId}`;
            } catch (err) {
                errorEl.textContent = '서버와 통신할 수 없습니다.';
            }
        };
    };

    // 초기화
    window.addEventListener('hashchange', router);
    router();
});
