// Script de limpieza definitivo para index.html
const fs = require('fs');
const path = 'index.html';
let content = fs.readFileSync(path, 'utf8');

// Encontrar la primera ocurrencia de "</body><script>" y cortar todo lo que esté después
const index = content.indexOf('</body><script>');
if (index !== -1) {
    content = content.substring(0, index) + '</body>\n</html>';
    fs.writeFileSync(path, content, 'utf8');
    console.log('Limpieza exitosa de index.html');
} else {
    console.log('No se encontraron duplicados');
}
