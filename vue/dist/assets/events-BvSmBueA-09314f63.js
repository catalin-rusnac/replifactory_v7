/*!
 * Built by Revolist OU ❤️
 */function u(t){return!!t.touches}function i(t,n){return!(n&&t&&!(t.target instanceof Element&&t.target.classList.contains(n)))}function o(t,n,e){if(u(t)){if(t.touches.length>0){const r=t.touches[0];return i(r,e)?r[n]||0:null}return null}return t[n]||0}export{o as g,i as v};
