// JavaScript для Chat Analyzer Bot

class ChatAnalyzerApp {
    constructor() {
        this.init();
    }

    init() {
        this.loadSystemStatus();
        this.loadRecentMessages();
        this.setupEventListeners();
    }

    async loadSystemStatus() {
        try {
            const response = await fetch('/api/system/status');
            const data = await response.json();
            
            if (data.success) {
                this.updateDashboardStats(data.data);
            } else {
                console.error('Ошибка загрузки статуса:', data.error);
            }
        } catch (error) {
            console.error('Ошибка сети:', error);
        }
    }

    updateDashboardStats(stats) {
        document.getElementById('total-chats').textContent = stats.total_chats || 0;
        document.getElementById('total-messages').textContent = stats.total_messages || 0;
        document.getElementById('total-users').textContent = stats.total_users || 0;
        document.getElementById('active-chats').textContent = stats.total_chats || 0;
    }

    async loadRecentMessages() {
        try {
            const response = await fetch('/api/system/status');
            const data = await response.json();
            
            if (data.success && data.data.recent_messages) {
                this.displayRecentMessages(data.data.recent_messages);
            } else {
                this.displayNoMessages();
            }
        } catch (error) {
            console.error('Ошибка загрузки сообщений:', error);
            this.displayErrorMessage();
        }
    }

    displayRecentMessages(messages) {
        const container = document.getElementById('recent-messages');
        
        if (messages.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-inbox fa-3x mb-3"></i>
                    <p>Нет сообщений для отображения</p>
                </div>
            `;
            return;
        }

        const messagesHtml = messages.map(message => `
            <div class="message-item mb-3 p-3 bg-light text-dark rounded">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <strong>${this.escapeHtml(message.user)}</strong>
                        <small class="text-muted ms-2">${message.date}</small>
                        <br>
                        <span class="text-primary">${this.escapeHtml(message.chat)}</span>
                    </div>
                </div>
                <div class="mt-2">
                    ${this.escapeHtml(message.text)}
                </div>
            </div>
        `).join('');

        container.innerHTML = messagesHtml;
        container.classList.add('fade-in');
    }

    displayNoMessages() {
        const container = document.getElementById('recent-messages');
        container.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-comments fa-3x mb-3"></i>
                <p>Нет сообщений для отображения</p>
                <small>Добавьте бота в группу и начните сбор данных</small>
            </div>
        `;
    }

    displayErrorMessage() {
        const container = document.getElementById('recent-messages');
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Ошибка загрузки сообщений
            </div>
        `;
    }

    setupEventListeners() {
        // Автообновление каждые 30 секунд
        setInterval(() => {
            this.loadSystemStatus();
            this.loadRecentMessages();
        }, 30000);

        // Обработка ошибок
        window.addEventListener('error', (event) => {
            console.error('Глобальная ошибка:', event.error);
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Автоматическое удаление через 5 секунд
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ChatAnalyzerApp();
});

// Утилиты для работы с API
class ApiClient {
    static async get(url) {
        try {
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    static async post(url, data) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }
}

// Функции для работы с группами
class ChatManager {
    static async getChats() {
        return await ApiClient.get('/api/chats');
    }

    static async getChatStats(chatId, days = 7) {
        return await ApiClient.get(`/api/chat/${chatId}/stats?days=${days}`);
    }

    static async getSystemStatus() {
        return await ApiClient.get('/api/system/status');
    }
}

// Функции для работы с графиками
class ChartManager {
    static createActivityChart(canvasId, data) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Активность',
                    data: data.values,
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        labels: {
                            color: '#fff'
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    }

    static createPieChart(canvasId, data) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        return new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: [
                        '#007bff',
                        '#28a745',
                        '#ffc107',
                        '#dc3545',
                        '#17a2b8'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        labels: {
                            color: '#fff'
                        }
                    }
                }
            }
        });
    }
}

// Экспорт для использования в других модулях
window.ChatAnalyzerApp = ChatAnalyzerApp;
window.ApiClient = ApiClient;
window.ChatManager = ChatManager;
window.ChartManager = ChartManager;
