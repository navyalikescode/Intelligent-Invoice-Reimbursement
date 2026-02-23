document.addEventListener('DOMContentLoaded', () => {

    // --- App Initialization ---
    const App = {
        init() {
            this.themeManager.init();
            this.ui.init();
            this.analysisForm.init();
            this.chatbot.init();
            this.heroAnimation.init();
        }
    };

    // --- Theme Management ---
    App.themeManager = {
        init() {
            this.themeToggle = document.getElementById('theme-toggle');
            this.body = document.body;
            this.themeToggle.addEventListener('click', () => this.toggleTheme());
            this.loadTheme();
        },
        loadTheme() {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'dark-mode') this.body.classList.add('dark-mode');
            else this.body.classList.remove('dark-mode');
        },
        toggleTheme() {
            this.body.classList.toggle('dark-mode');
            localStorage.setItem('theme', this.body.classList.contains('dark-mode') ? 'dark-mode' : 'light-mode');
        }
    };

    // --- UI Enhancements ---
    App.ui = {
        init() {
            this.initScrollToTop();
            this.initScrollAnimations();
            this.initFileInputs();
        },
        showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            container.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        },
        initScrollToTop() {
            const btn = document.getElementById('scrollToTopBtn');
            window.addEventListener('scroll', () => {
                if (window.scrollY > 300) btn.classList.add('visible');
                else btn.classList.remove('visible');
            });
            btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
        },
        initScrollAnimations() {
            const elements = document.querySelectorAll('.animate-on-scroll');
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) entry.target.classList.add('visible');
                });
            }, { threshold: 0.1 });
            elements.forEach(el => observer.observe(el));
        },
        initFileInputs() {
            document.querySelectorAll('input[type="file"]').forEach(input => {
                input.addEventListener('change', (e) => {
                    const fileName = e.target.files[0] ? e.target.files[0].name : 'Choose a file...';
                    e.target.nextElementSibling.querySelector('.file-input-text').textContent = fileName;
                });
            });
        }
    };

    // --- Invoice Analysis Form ---
    App.analysisForm = {
        init() {
            this.form = document.getElementById('analysisForm');
            if (!this.form) return;
            this.submitBtn = document.getElementById('analyzeBtn');
            this.resultDiv = document.getElementById('analysisResult');
            this.resultActions = document.getElementById('resultActions');
            this.downloadBtn = document.getElementById('downloadJsonBtn');
            this.copyBtn = document.getElementById('copyJsonBtn');
            this.lastResult = null;

            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
            this.form.addEventListener('input', () => this.validateForm());
            this.downloadBtn.addEventListener('click', () => this.downloadJson());
            this.copyBtn.addEventListener('click', () => this.copyJson());
        },
        validateForm() {
            this.submitBtn.disabled = !this.form.checkValidity();
        },
        async handleSubmit(e) {
            e.preventDefault();
            this.submitBtn.classList.add('loading');
            this.resultDiv.style.display = 'none';
            this.resultActions.style.display = 'none';

            try {
                const response = await fetch('/analyze-invoices/', { method: 'POST', body: new FormData(this.form) });
                const result = await response.json();
                this.lastResult = result;

                if (response.ok) {
                    this.resultDiv.innerHTML = `<pre>${this.syntaxHighlight(result)}</pre>`;
                    this.resultDiv.style.display = 'block';
                    this.resultActions.style.display = 'flex';
                } else {
                    App.ui.showToast(`Error: ${result.detail || response.statusText}`, 'error');
                }
            } catch (error) {
                App.ui.showToast(`Network error: ${error.message}`, 'error');
            } finally {
                this.submitBtn.classList.remove('loading');
            }
        },
        downloadJson() {
            if (!this.lastResult) return;
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.lastResult, null, 2));
            const anchor = document.createElement('a');
            anchor.setAttribute("href", dataStr);
            anchor.setAttribute("download", "invoice_analysis_result.json");
            document.body.appendChild(anchor);
            anchor.click();
            anchor.remove();
        },
        copyJson() {
            if (!this.lastResult) return;
            navigator.clipboard.writeText(JSON.stringify(this.lastResult, null, 2))
                .then(() => App.ui.showToast('Copied to clipboard!'))
                .catch(() => App.ui.showToast('Failed to copy.', 'error'));
        },
        syntaxHighlight(json) {
            if (typeof json != 'string') json = JSON.stringify(json, undefined, 2);
            json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return json.replace(/("(\\u[a-zA-Z0-9]{4}|[^\\"])*?")|(\b(true|false|null)\b)|(-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
                let cls = 'json-number';
                if (/^"/.test(match)) cls = /:$/.test(match) ? 'json-key' : 'json-string';
                else if (/true|false/.test(match)) cls = 'json-boolean';
                else if (/null/.test(match)) cls = 'json-null';
                return `<span class="${cls}">${match}</span>`;
            });
        }
    };

    // --- Chatbot ---
    App.chatbot = {
        init() {
            this.form = document.getElementById('chatbotForm');
            if (!this.form) return;
            this.submitBtn = document.getElementById('chatbotBtn');
            this.queryInput = document.getElementById('chatbotQuery');
            this.history = document.getElementById('chatHistory');
            this.viewport = document.getElementById('chatbot-viewport');
            this.typingIndicator = document.getElementById('typing-indicator');
            this.clearBtn = document.getElementById('clearChatBtn');
            this.suggestions = document.getElementById('chatbot-suggestions');

            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
            this.clearBtn.addEventListener('click', () => this.clearChat());
            this.suggestions.addEventListener('click', (e) => this.handleSuggestion(e));
        },
        async handleSubmit(e) {
            e.preventDefault();
            const query = this.queryInput.value.trim();
            if (!query) return;

            this.submitBtn.classList.add('loading');
            this.typingIndicator.style.display = 'flex';
            this.appendMessage(query, 'user-message');
            this.queryInput.value = '';

            const employeeName = document.getElementById('employeeNameChatbot').value;
            const params = new URLSearchParams({ query });
            if (employeeName) params.append('employee_name', employeeName);

            try {
                const response = await fetch(`/chatbot/?${params.toString()}`, { method: 'POST' });
                const result = await response.json();
                const message = response.ok ? marked.parse(result.response) : `Error: ${result.detail || response.statusText}`;
                this.appendMessage(message, 'bot-message');
            } catch (error) {
                this.appendMessage(`Network error: ${error.message}`, 'bot-message');
            } finally {
                this.submitBtn.classList.remove('loading');
                this.typingIndicator.style.display = 'none';
            }
        },
        handleSuggestion(e) {
            if (e.target.classList.contains('suggestion-chip')) {
                this.queryInput.value = e.target.textContent;
                this.form.requestSubmit();
            }
        },
        appendMessage(content, className) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `chat-message ${className}`;
            messageDiv.innerHTML = content;
            this.history.appendChild(messageDiv);
            this.viewport.scrollTop = this.viewport.scrollHeight;
        },
        clearChat() {
            this.history.innerHTML = '';
        }
    };

    // --- Hero Animation ---
    App.heroAnimation = {
        init() {
            const container = document.getElementById('hero-animation');
            if (container) {
                lottie.loadAnimation({
                    container: container,
                    renderer: 'svg',
                    loop: true,
                    autoplay: true,
                    path: 'https://assets9.lottiefiles.com/packages/lf20_v1yudlrx.json' // Example Lottie animation
                });
            }
        }
    };

    App.init();
});