// JavaScript для панели управления

class Dashboard {
    constructor() {
        this.init();
    }

    init() {
        this.loadSystemStatus();
        this.loadCharts();
        this.loadTopUsers();
        this.loadPopularTopics();
        this.setupAutoRefresh();
    }

    async loadSystemStatus() {
        try {
            const response = await fetch('/api/system/status');
            const data = await response.json();
            
            if (data.success) {
                this.updateStats(data.data);
            } else {
                console.error('Ошибка загрузки статуса:', data.error);
            }
        } catch (error) {
            console.error('Ошибка сети:', error);
        }
    }

    updateStats(stats) {
        document.getElementById('total-chats').textContent = stats.total_chats || 0;
        document.getElementById('total-messages').textContent = stats.total_messages || 0;
        document.getElementById('total-users').textContent = stats.total_users || 0;
        document.getElementById('active-chats').textContent = stats.total_chats || 0;
    }

    async loadCharts() {
        try {
            // График активности по дням
            const activityCtx = document.getElementById('activityChart').getContext('2d');
            const activityChart = new Chart(activityCtx, {
                type: 'line',
                data: {
                    labels: ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
                    datasets: [{
                        label: 'Сообщений',
                        data: [65, 59, 80, 81, 56, 55, 40],
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

            // График распределения по группам
            const groupsCtx = document.getElementById('groupsChart').getContext('2d');
            const groupsChart = new Chart(groupsCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Группа 1', 'Группа 2', 'Группа 3', 'Группа 4'],
                    datasets: [{
                        data: [300, 250, 200, 150],
                        backgroundColor: [
                            '#007bff',
                            '#28a745',
                            '#ffc107',
                            '#dc3545'
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

        } catch (error) {
            console.error('Ошибка загрузки графиков:', error);
        }
    }

    async loadTopUsers() {
        try {
            const response = await fetch('/api/system/status');
            const data = await response.json();
            
            if (data.success && data.data.recent_messages) {
                this.displayTopUsers(data.data.recent_messages);
            } else {
                this.displayNoTopUsers();
            }
        } catch (error) {
            console.error('Ошибка загрузки топ пользователей:', error);
            this.displayNoTopUsers();
        }
    }

    displayTopUsers(messages) {
        const container = document.getElementById('top-users');
        
        // Группируем сообщения по пользователям
        const userStats = {};
        messages.forEach(message => {
            if (!userStats[message.user]) {
                userStats[message.user] = { count: 0, lastMessage: message.date };
            }
            userStats[message.user].count++;
        });

        // Сортируем по количеству сообщений
        const topUsers = Object.entries(userStats)
            .sort(([,a], [,b]) => b.count - a.count)
            .slice(0, 5);

        if (topUsers.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-users fa-2x mb-2"></i>
                    <p>Нет данных о пользователях</p>
                </div>
            `;
            return;
        }

        const usersHtml = topUsers.map(([user, stats], index) => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div class="d-flex align-items-center">
                    <span class="badge bg-primary me-2">${index + 1}</span>
                    <div>
                        <strong>${this.escapeHtml(user)}</strong>
                        <br>
                        <small class="text-muted">${stats.count} сообщений</small>
                    </div>
                </div>
                <small class="text-muted">${stats.lastMessage}</small>
            </div>
        `).join('');

        container.innerHTML = usersHtml;
    }

    displayNoTopUsers() {
        const container = document.getElementById('top-users');
        container.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-users fa-2x mb-2"></i>
                <p>Нет данных о пользователях</p>
                <small>Добавьте бота в группу для сбора данных</small>
            </div>
        `;
    }

    async loadPopularTopics() {
        try {
            const response = await fetch('/api/system/status');
            const data = await response.json();
            
            if (data.success && data.data.recent_messages) {
                this.displayPopularTopics(data.data.recent_messages);
            } else {
                this.displayNoTopics();
            }
        } catch (error) {
            console.error('Ошибка загрузки тем:', error);
            this.displayNoTopics();
        }
    }

    displayPopularTopics(messages) {
        const container = document.getElementById('popular-topics');
        
        // Извлекаем слова из сообщений
        const words = messages
            .map(msg => msg.text.toLowerCase())
            .join(' ')
            .split(/\s+/)
            .filter(word => word.length > 3)
            .filter(word => !['это', 'что', 'как', 'где', 'когда', 'почему'].includes(word));

        // Подсчитываем частоту
        const wordCount = {};
        words.forEach(word => {
            wordCount[word] = (wordCount[word] || 0) + 1;
        });

        // Топ-5 слов
        const topWords = Object.entries(wordCount)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 5);

        if (topWords.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-fire fa-2x mb-2"></i>
                    <p>Нет данных о темах</p>
                </div>
            `;
            return;
        }

        const topicsHtml = topWords.map(([word, count], index) => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div class="d-flex align-items-center">
                    <span class="badge bg-warning me-2">${index + 1}</span>
                    <strong>${this.escapeHtml(word)}</strong>
                </div>
                <span class="badge bg-secondary">${count}</span>
            </div>
        `).join('');

        container.innerHTML = topicsHtml;
    }

    displayNoTopics() {
        const container = document.getElementById('popular-topics');
        container.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-fire fa-2x mb-2"></i>
                <p>Нет данных о темах</p>
                <small>Добавьте бота в группу для анализа</small>
            </div>
        `;
    }

    setupAutoRefresh() {
        // Автообновление каждые 30 секунд
        setInterval(() => {
            this.loadSystemStatus();
            this.loadTopUsers();
            this.loadPopularTopics();
        }, 30000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Инициализация панели управления
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});
