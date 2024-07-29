class ShadowComponent extends HTMLElement {
    constructor() {
        super();
        const shadow = this.attachShadow({ mode: 'open' });

        const style = document.createElement('style');
        style.textContent = `
            @import url('/static/index-G1GaC6Sm.css');
            /* Add any additional styles here */
        `;

        const wrapper = document.createElement('div');
        wrapper.innerHTML = `
            <div id="specific-div">
            </div>
        `;

        shadow.appendChild(style);
        shadow.appendChild(wrapper);
    }
}

customElements.define('shadow-component', ShadowComponent);
