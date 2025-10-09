(function(){"use strict";self.onmessage=o=>{const n=o.data,e={};for(let s=0;s<n.length;s++){const i=n[s];if(i.pixel_set)for(let t of i.pixel_set)e[t]||(e[t]=[]),e[t].push(s)}self.postMessage(e)}})();
