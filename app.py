const express = require('express');
const path = require('path');
const app = express();

// Configurar o Express para servir arquivos estáticos
app.use(express.static(path.join(__dirname, 'public')));

// Configurar o Express para usar HTML como template
app.get('/', (req, res) => {
    const statesCities = {
        "AC": ["Rio Branco", "Cruzeiro do Sul", "Sena Madureira", "Tarauacá", "Feijó", 
               "Brasiléia", "Xapuri", "Senador Guiomard", "Plácido de Castro", "Mâncio Lima"],
        "AL": ["Maceió", "Arapiraca", "Palmeira dos Índios", "Rio Largo", "Penedo", 
               "União dos Palmares", "São Miguel dos Campos", "Coruripe", "Delmiro Gouveia", "Marechal Deodoro"],
    };
    res.sendFile(path.join(__dirname, 'views', 'index.html'));
    // Para passar dados para o frontend, você pode usar uma API ou injetar diretamente no HTML
    app.get('/states', (req, res) => {
        res.json(Object.keys(statesCities));
    });
});

// Iniciar o servidor
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Servidor rodando na porta ${PORT}`);
});