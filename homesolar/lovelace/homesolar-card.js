/**
 * HomeSolar Lovelace Card
 * Carte personnalisée pour Home Assistant affichant l'éphéméride solaire
 */

class HomeSolarCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this._config = {};
        this._hass = null;
        this._solarData = null;
        this._updateInterval = null;
    }

    set hass(hass) {
        this._hass = hass;
        if (!this._solarData) {
            this._fetchData();
        }
    }

    setConfig(config) {
        if (!config.addon_slug) {
            config.addon_slug = 'homesolar';
        }
        this._config = config;
        this._render();
    }

    connectedCallback() {
        this._fetchData();
        // Rafraîchir toutes les 5 minutes
        this._updateInterval = setInterval(() => this._fetchData(), 5 * 60 * 1000);
    }

    disconnectedCallback() {
        if (this._updateInterval) {
            clearInterval(this._updateInterval);
        }
    }

    async _fetchData() {
        try {
            // Utiliser l'API de l'addon via ingress
            const response = await fetch(`/api/hassio_ingress/${this._config.addon_slug}/api/solar`);
            if (response.ok) {
                this._solarData = await response.json();
                this._render();
            }
        } catch (error) {
            console.error('HomeSolar: Erreur de chargement', error);
        }
    }

    _render() {
        if (!this._solarData) {
            this.shadowRoot.innerHTML = `
                <ha-card header="☀️ HomeSolar">
                    <div class="card-content loading">
                        <ha-circular-progress active></ha-circular-progress>
                        <p>Chargement des données solaires...</p>
                    </div>
                </ha-card>
                <style>
                    .loading {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        padding: 20px;
                        gap: 10px;
                    }
                </style>
            `;
            return;
        }

        const data = this._solarData;
        
        this.shadowRoot.innerHTML = `
            <ha-card>
                <div class="card-content">
                    <div class="header">
                        <span class="title">☀️ Éphéméride Solaire HomeSolar</span>
                        <span class="date">${data.date}</span>
                    </div>
                    
                    <div class="main-info">
                        <div class="info-item sunrise">
                            <span class="icon">🌅</span>
                            <div class="details">
                                <span class="label">Lever</span>
                                <span class="value">${data.sunrise || '--:--'}</span>
                            </div>
                        </div>
                        
                        <div class="info-item sunset">
                            <span class="icon">🌇</span>
                            <div class="details">
                                <span class="label">Coucher</span>
                                <span class="value">${data.sunset || '--:--'}</span>
                            </div>
                        </div>
                        
                        <div class="info-item duration">
                            <span class="icon">⏱️</span>
                            <div class="details">
                                <span class="label">Durée</span>
                                <span class="value">${data.day_length}</span>
                                <span class="diff ${data.diff_positive ? 'positive' : 'negative'}">
                                    ${data.diff_sign}${data.diff}
                                </span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="progress-section">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${data.progress.progress}%"></div>
                            <div class="progress-indicator" style="left: ${data.progress.progress}%"></div>
                        </div>
                        <div class="progress-labels">
                            <span>${data.progress.is_day ? data.sunrise : data.sunset}</span>
                            <span class="phase">${data.phase.icon} ${data.phase.phase}</span>
                            <span>${data.progress.is_day ? data.sunset : data.sunrise}</span>
                        </div>
                    </div>
                    
                    ${this._config.show_twilights ? `
                    <div class="twilights">
                        <div class="twilight-row">
                            <span class="tw-label">Aube civile</span>
                            <span class="tw-value">${data.civil_dawn || '--:--'}</span>
                        </div>
                        <div class="twilight-row">
                            <span class="tw-label">Aube nautique</span>
                            <span class="tw-value">${data.nautical_dawn || '--:--'}</span>
                        </div>
                        <div class="twilight-row">
                            <span class="tw-label">Crép. civil</span>
                            <span class="tw-value">${data.civil_dusk || '--:--'}</span>
                        </div>
                        <div class="twilight-row">
                            <span class="tw-label">Crép. nautique</span>
                            <span class="tw-value">${data.nautical_dusk || '--:--'}</span>
                        </div>
                    </div>
                    ` : ''}
                </div>
            </ha-card>
            
            <style>
                ha-card {
                    padding: 0;
                }
                
                .card-content {
                    padding: 16px;
                }
                
                .header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 16px;
                }
                
                .title {
                    font-size: 18px;
                    font-weight: 500;
                }
                
                .date {
                    font-size: 12px;
                    opacity: 0.7;
                    text-transform: capitalize;
                }
                
                .main-info {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 12px;
                    margin-bottom: 16px;
                }
                
                .info-item {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 12px;
                    background: var(--secondary-background-color, rgba(255,255,255,0.05));
                    border-radius: 8px;
                }
                
                .icon {
                    font-size: 24px;
                }
                
                .details {
                    display: flex;
                    flex-direction: column;
                }
                
                .label {
                    font-size: 11px;
                    opacity: 0.7;
                    text-transform: uppercase;
                }
                
                .value {
                    font-size: 18px;
                    font-weight: 500;
                }
                
                .diff {
                    font-size: 11px;
                    padding: 2px 6px;
                    border-radius: 4px;
                    margin-top: 4px;
                    display: inline-block;
                    width: fit-content;
                }
                
                .diff.positive {
                    background: rgba(76, 175, 80, 0.2);
                    color: #4caf50;
                }
                
                .diff.negative {
                    background: rgba(244, 67, 54, 0.2);
                    color: #f44336;
                }
                
                .progress-section {
                    margin: 16px 0;
                }
                
                .progress-bar {
                    position: relative;
                    height: 8px;
                    background: linear-gradient(to right, #3b82f6, #fbbf24, #f59e0b, #fbbf24, #3b82f6);
                    border-radius: 4px;
                    overflow: visible;
                }
                
                .progress-fill {
                    height: 100%;
                    background: transparent;
                }
                
                .progress-indicator {
                    position: absolute;
                    top: 50%;
                    transform: translate(-50%, -50%);
                    width: 16px;
                    height: 16px;
                    background: white;
                    border-radius: 50%;
                    box-shadow: 0 0 6px rgba(0,0,0,0.3);
                }
                
                .progress-labels {
                    display: flex;
                    justify-content: space-between;
                    margin-top: 8px;
                    font-size: 12px;
                    opacity: 0.7;
                }
                
                .phase {
                    font-weight: 500;
                    opacity: 1;
                }
                
                .twilights {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 8px;
                    margin-top: 16px;
                    padding-top: 16px;
                    border-top: 1px solid var(--divider-color, rgba(255,255,255,0.1));
                }
                
                .twilight-row {
                    display: flex;
                    justify-content: space-between;
                    font-size: 12px;
                }
                
                .tw-label {
                    opacity: 0.7;
                }
                
                .tw-value {
                    font-weight: 500;
                }
            </style>
        `;
    }

    getCardSize() {
        return this._config.show_twilights ? 5 : 4;
    }

    static getConfigElement() {
        return document.createElement('mamasoleil-card-editor');
    }

    static getStubConfig() {
        return {
            addon_slug: 'mamasoleil',
            show_twilights: true
        };
    }
}

// Éditeur de configuration
class HomeSolarCardEditor extends HTMLElement {
    setConfig(config) {
        this._config = config;
        this._render();
    }

    _render() {
        this.innerHTML = `
            <div style="padding: 16px;">
                <ha-formfield label="Afficher les crépuscules">
                    <ha-switch 
                        id="show_twilights" 
                        ${this._config.show_twilights ? 'checked' : ''}
                    ></ha-switch>
                </ha-formfield>
            </div>
        `;

        this.querySelector('#show_twilights').addEventListener('change', (e) => {
            this._config = { ...this._config, show_twilights: e.target.checked };
            this._fireEvent();
        });
    }

    _fireEvent() {
        const event = new CustomEvent('config-changed', {
            detail: { config: this._config },
            bubbles: true,
            composed: true
        });
        this.dispatchEvent(event);
    }
}

// Enregistrer les composants
customElements.define('homesolar-card', HomeSolarCard);
customElements.define('homesolar-card-editor', HomeSolarCardEditor);

// Enregistrer la carte dans Home Assistant
window.customCards = window.customCards || [];
window.customCards.push({
    type: 'homesolar-card',
    name: 'HomeSolar',
    description: 'Éphéméride solaire complet avec lever/coucher du soleil et crépuscules',
    preview: true
});
