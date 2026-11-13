//vodoznak s klucom testu a casom cez celu obrazovku: snimka obrazovky prezradi, z ktorej relacie pochadza (len pre ziaka, ucitel ho nema)
document.addEventListener('DOMContentLoaded', () => {
   const vodoznak = document.getElementById('vodoznak');
   if (!vodoznak) return;
   const kluc = vodoznak.dataset.kluc || '';
   const text = document.createElement('div');
   text.className = 'vodoznak-text';
   vodoznak.appendChild(text);
   const nakresli = () => {
      const cas = new Date().toLocaleTimeString('sk-SK', { hour: '2-digit', minute: '2-digit' });
      //jeden opakovany retazec je siroky asi (dlzka + 8) * 9 px a riadok ma 64 px; plocha je 200 % x 200 % obrazovky
      const pocet = Math.ceil((4 * window.innerWidth * window.innerHeight) / ((kluc.length + 8) * 9 * 64));
      text.textContent = `${kluc} ${cas}  `.repeat(Math.max(pocet, 40));
   };
   nakresli();
   setInterval(nakresli, 30000);
   window.addEventListener('resize', nakresli);
});
