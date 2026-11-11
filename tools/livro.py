"""Livro de receitas reais — o agente nunca inventa um prato sem sentido.

Usado quando nao ha IA (ou a IA falha). Cada prato tem os ingredientes
PRINCIPAIS (o utilizador tem de os ter todos para o prato ser escolhido) e os
restantes, que o agente vai comprar. Ganha o prato que aproveita MAIS
ingredientes principais do utilizador: "frango e batatas" -> frango frito com
batata frita, e nao um "frango salteado" qualquer.

Os nomes dos ingredientes batem com o catalogo (data/catalog.json).
"""

PRATOS = [
    {
        "principais": ["frango", "batata"],
        "pt": {
            "titulo": "Frango frito com batata frita",
            "descricao": "Frango estaladiço por fora e suculento por dentro, com batatas fritas caseiras.",
            "ingredientes": ["frango", "batata", "farinha", "ovo", "alho", "limão", "sal", "pimenta", "óleo"],
            "passos": [
                "Corta o frango em pedaços e tempera com alho picado, sumo de limão, sal e pimenta; deixa 20 min.",
                "Descasca as batatas, corta em palitos, passa por água fria e seca bem com um pano.",
                "Passa o frango por ovo batido e depois por farinha temperada com sal e pimenta.",
                "Frita o frango em óleo a 170 °C durante 12–15 min, até dourar e o interior deixar de estar rosado.",
                "Frita as batatas em óleo bem quente até ficarem douradas, escorre, polvilha com sal e serve com o frango.",
            ],
        },
        "en": {
            "titulo": "Fried chicken with French fries",
            "descricao": "Crispy-outside, juicy-inside fried chicken with homemade fries.",
            "ingredientes": ["chicken", "potato", "flour", "egg", "garlic", "lemon", "salt", "pepper", "oil"],
            "passos": [
                "Cut the chicken into pieces and season with minced garlic, lemon juice, salt and pepper; rest 20 min.",
                "Peel the potatoes, cut into sticks, rinse in cold water and pat completely dry.",
                "Dip the chicken in beaten egg, then in flour seasoned with salt and pepper.",
                "Fry the chicken in oil at 170 °C (340 °F) for 12–15 min, until golden and no longer pink inside.",
                "Fry the potatoes in very hot oil until golden, drain, salt and serve with the chicken.",
            ],
        },
    },
    {
        "principais": ["arroz", "peixe"],
        "pt": {
            "titulo": "Arroz de peixe",
            "descricao": "O clássico arroz malandrinho de peixe, com tomate, pimento e coentros.",
            "ingredientes": ["arroz", "peixe", "tomate", "cebola", "alho", "pimento", "coentros", "azeite", "sal"],
            "passos": [
                "Corta o peixe em postas, tempera com sal e reserva.",
                "Num tacho, refoga a cebola, o alho e o pimento picados em azeite durante 5 min.",
                "Junta o tomate picado e deixa apurar 5 min, até desfazer.",
                "Acrescenta o arroz e o triplo de água a ferver, tempera com sal e coze 10 min.",
                "Junta o peixe, coze mais 6–8 min (o arroz deve ficar malandrinho) e termina com coentros picados.",
            ],
        },
        "en": {
            "titulo": "Portuguese fish rice (arroz de peixe)",
            "descricao": "A classic, soupy fish rice with tomato, bell pepper and coriander.",
            "ingredientes": ["rice", "fish", "tomato", "onion", "garlic", "bell pepper", "coriander", "olive oil", "salt"],
            "passos": [
                "Cut the fish into chunks, season with salt and set aside.",
                "In a pot, sauté chopped onion, garlic and bell pepper in olive oil for 5 min.",
                "Add the chopped tomato and cook 5 min until it breaks down.",
                "Add the rice and three times its volume of boiling water, season and simmer 10 min.",
                "Add the fish, cook 6–8 min more (it should stay loose and saucy) and finish with chopped coriander.",
            ],
        },
    },
    {
        "principais": ["fuba", "peixe"],
        "pt": {
            "titulo": "Funge com calulu de peixe",
            "descricao": "O prato angolano de sempre: calulu de peixe com quiabo e óleo de palma, servido com funge.",
            "ingredientes": ["fuba", "peixe", "óleo de palma", "quiabo", "couve", "tomate", "cebola", "alho", "sal"],
            "passos": [
                "Tempera o peixe com sal e alho e reserva.",
                "Num tacho, faz camadas de cebola, tomate, quiabo e couve; põe o peixe por cima e rega com óleo de palma.",
                "Junta um pouco de água, tapa e coze em lume brando 25 min, sem mexer.",
                "Para o funge, leva água a ferver, junta a fuba aos poucos e mexe com força até ficar uma massa lisa e elástica.",
                "Serve o calulu bem quente ao lado do funge.",
            ],
        },
        "en": {
            "titulo": "Funge with fish calulu (Angola)",
            "descricao": "Angola's classic: fish stewed with okra, greens and red palm oil, served with funge.",
            "ingredientes": ["cassava flour", "fish", "palm oil", "okra", "collard greens", "tomato", "onion", "garlic", "salt"],
            "passos": [
                "Season the fish with salt and garlic and set aside.",
                "In a pot, layer onion, tomato, okra and greens; put the fish on top and drizzle with palm oil.",
                "Add a little water, cover and simmer 25 min without stirring.",
                "For the funge, bring water to a boil, add the cassava flour little by little and beat hard until smooth and elastic.",
                "Serve the calulu hot next to the funge.",
            ],
        },
    },
    {
        "principais": ["frango", "arroz"],
        "pt": {
            "titulo": "Arroz de frango",
            "descricao": "Arroz de frango caseiro, solto e cheio de sabor.",
            "ingredientes": ["frango", "arroz", "cebola", "alho", "tomate", "pimento", "azeite", "sal", "salsa"],
            "passos": [
                "Corta o frango em pedaços, tempera com sal e alho e aloura-o em azeite; reserva.",
                "No mesmo tacho, refoga a cebola e o pimento 5 min e junta o tomate picado.",
                "Volta a pôr o frango, cobre com água e coze 15 min.",
                "Junta o arroz (1 chávena para 2,5 de caldo), retifica o sal e coze 15 min em lume brando.",
                "Deixa repousar 5 min tapado e serve com salsa picada.",
            ],
        },
        "en": {
            "titulo": "Chicken and rice",
            "descricao": "Homestyle chicken and rice, fluffy and full of flavour.",
            "ingredientes": ["chicken", "rice", "onion", "garlic", "tomato", "bell pepper", "olive oil", "salt", "parsley"],
            "passos": [
                "Cut the chicken, season with salt and garlic and brown it in olive oil; set aside.",
                "In the same pot, sauté onion and bell pepper 5 min, then add chopped tomato.",
                "Return the chicken, cover with water and simmer 15 min.",
                "Add the rice (1 cup per 2.5 cups of stock), adjust salt and cook 15 min on low heat.",
                "Rest 5 min covered and serve with chopped parsley.",
            ],
        },
    },
    {
        "principais": ["ovo", "batata"],
        "pt": {
            "titulo": "Tortilha de batata",
            "descricao": "Tortilha de batata e cebola, dourada por fora e cremosa por dentro.",
            "ingredientes": ["ovo", "batata", "cebola", "azeite", "sal"],
            "passos": [
                "Corta as batatas em rodelas finas e a cebola em meias-luas.",
                "Coze-as em bastante azeite em lume médio 15–20 min, até ficarem macias sem dourar; escorre.",
                "Bate os ovos com sal, junta as batatas e a cebola e deixa repousar 5 min.",
                "Numa frigideira com um fio de azeite, coze 4 min, vira com a ajuda de um prato e coze mais 3 min.",
            ],
        },
        "en": {
            "titulo": "Spanish potato omelette (tortilla)",
            "descricao": "Potato and onion omelette, golden outside and creamy inside.",
            "ingredientes": ["egg", "potato", "onion", "olive oil", "salt"],
            "passos": [
                "Slice the potatoes thinly and the onion into half-moons.",
                "Cook them in plenty of olive oil over medium heat 15–20 min until soft but not browned; drain.",
                "Beat the eggs with salt, fold in the potatoes and onion and rest 5 min.",
                "Cook in a pan with a little oil for 4 min, flip using a plate and cook 3 min more.",
            ],
        },
    },
    {
        "principais": ["ovo", "farinha", "leite"],
        "pt": {
            "titulo": "Panquecas",
            "descricao": "Panquecas fofas para o pequeno-almoço.",
            "ingredientes": ["ovo", "farinha", "leite", "manteiga", "açúcar", "sal"],
            "passos": [
                "Mistura 200 g de farinha, 1 colher de açúcar e uma pitada de sal.",
                "Junta 2 ovos, 300 ml de leite e 30 g de manteiga derretida e bate até ficar liso.",
                "Deixa a massa repousar 10 min.",
                "Coze conchas de massa numa frigideira untada em lume médio, 1–2 min de cada lado.",
            ],
        },
        "en": {
            "titulo": "Fluffy pancakes",
            "descricao": "Classic fluffy breakfast pancakes.",
            "ingredientes": ["egg", "flour", "milk", "butter", "sugar", "salt"],
            "passos": [
                "Mix 200 g flour, 1 tbsp sugar and a pinch of salt.",
                "Add 2 eggs, 300 ml milk and 30 g melted butter and whisk until smooth.",
                "Rest the batter 10 min.",
                "Cook ladlefuls in a greased pan over medium heat, 1–2 min per side.",
            ],
        },
    },
    {
        "principais": ["massa", "tomate"],
        "pt": {
            "titulo": "Esparguete com molho de tomate",
            "descricao": "Esparguete com um molho de tomate caseiro e queijo por cima.",
            "ingredientes": ["massa", "tomate", "cebola", "alho", "azeite", "sal", "queijo"],
            "passos": [
                "Refoga a cebola e o alho picados em azeite durante 5 min.",
                "Junta o tomate picado, tempera com sal e deixa apurar 15 min em lume brando.",
                "Coze a massa em água a ferver com sal segundo o tempo da embalagem.",
                "Escorre, envolve no molho e serve com queijo ralado.",
            ],
        },
        "en": {
            "titulo": "Spaghetti with tomato sauce",
            "descricao": "Spaghetti in a homemade tomato sauce, topped with cheese.",
            "ingredientes": ["spaghetti", "tomato", "onion", "garlic", "olive oil", "salt", "cheese"],
            "passos": [
                "Sauté chopped onion and garlic in olive oil for 5 min.",
                "Add chopped tomato, season with salt and simmer 15 min.",
                "Boil the pasta in salted water for the time on the pack.",
                "Drain, toss in the sauce and serve with grated cheese.",
            ],
        },
    },
    {
        "principais": ["feijão"],
        "pt": {
            "titulo": "Feijão de óleo de palma",
            "descricao": "Feijão angolano cremoso, cozinhado em óleo de palma.",
            "ingredientes": ["feijão", "óleo de palma", "cebola", "alho", "sal"],
            "passos": [
                "Demolha o feijão de véspera e coze-o em água até ficar macio (cerca de 1 h).",
                "Num tacho, aquece o óleo de palma e refoga a cebola e o alho picados.",
                "Junta o feijão com um pouco da água da cozedura e tempera com sal.",
                "Deixa apurar 15 min em lume brando, mexendo, até ficar cremoso.",
            ],
        },
        "en": {
            "titulo": "Angolan palm-oil beans",
            "descricao": "Creamy Angolan beans cooked in red palm oil.",
            "ingredientes": ["beans", "palm oil", "onion", "garlic", "salt"],
            "passos": [
                "Soak the beans overnight and boil until tender (about 1 h).",
                "Heat the palm oil in a pot and sauté chopped onion and garlic.",
                "Add the beans with some of their cooking water and season with salt.",
                "Simmer 15 min, stirring, until creamy.",
            ],
        },
    },
    {
        "principais": ["frango"],
        "pt": {
            "titulo": "Frango grelhado com gindungo",
            "descricao": "Frango grelhado à angolana, picante, com limão e alho.",
            "ingredientes": ["frango", "gindungo", "limão", "alho", "azeite", "sal"],
            "passos": [
                "Abre o frango (ou usa coxas) e tempera com alho, sumo de limão, gindungo, sal e azeite.",
                "Deixa marinar pelo menos 30 min.",
                "Grelha em lume médio 30–35 min, virando e pincelando com a marinada.",
                "Está pronto quando o suco sair transparente; serve com mais gindungo à parte.",
            ],
        },
        "en": {
            "titulo": "Grilled piri-piri chicken",
            "descricao": "Angolan-style spicy grilled chicken with lemon and garlic.",
            "ingredientes": ["chicken", "chili", "lemon", "garlic", "olive oil", "salt"],
            "passos": [
                "Butterfly the chicken (or use thighs) and rub with garlic, lemon juice, chili, salt and olive oil.",
                "Marinate at least 30 min.",
                "Grill over medium heat 30–35 min, turning and brushing with the marinade.",
                "It's done when the juices run clear; serve with extra chili on the side.",
            ],
        },
    },
    {
        "principais": ["peixe"],
        "pt": {
            "titulo": "Peixe grelhado com batata cozida",
            "descricao": "Peixe grelhado simples com batata cozida, azeite e salsa.",
            "ingredientes": ["peixe", "batata", "limão", "alho", "azeite", "sal", "salsa"],
            "passos": [
                "Tempera o peixe com sal e limão e deixa 10 min.",
                "Coze as batatas descascadas em água com sal durante 20 min.",
                "Grelha o peixe 4–5 min de cada lado.",
                "Serve com as batatas, rega com azeite e alho picado e polvilha com salsa.",
            ],
        },
        "en": {
            "titulo": "Grilled fish with boiled potatoes",
            "descricao": "Simple grilled fish with boiled potatoes, olive oil and parsley.",
            "ingredientes": ["fish", "potato", "lemon", "garlic", "olive oil", "salt", "parsley"],
            "passos": [
                "Season the fish with salt and lemon and rest 10 min.",
                "Boil the peeled potatoes in salted water for 20 min.",
                "Grill the fish 4–5 min per side.",
                "Serve with the potatoes, drizzle with olive oil and minced garlic and sprinkle with parsley.",
            ],
        },
    },
    {
        "principais": ["batata"],
        "pt": {
            "titulo": "Batata frita caseira",
            "descricao": "Batatas fritas caseiras, estaladiças, com sal.",
            "ingredientes": ["batata", "óleo", "sal"],
            "passos": [
                "Descasca as batatas e corta em palitos de 1 cm.",
                "Passa por água fria e seca muito bem.",
                "Frita em óleo a 160 °C durante 5 min, retira e deixa arrefecer.",
                "Volta a fritar a 190 °C 2–3 min até dourar; escorre e tempera com sal.",
            ],
        },
        "en": {
            "titulo": "Homemade French fries",
            "descricao": "Crispy double-fried homemade fries.",
            "ingredientes": ["potato", "oil", "salt"],
            "passos": [
                "Peel the potatoes and cut into 1 cm sticks.",
                "Rinse in cold water and dry very well.",
                "Fry at 160 °C (320 °F) for 5 min, remove and let cool.",
                "Fry again at 190 °C (375 °F) for 2–3 min until golden; drain and salt.",
            ],
        },
    },
    {
        "principais": ["ovo"],
        "pt": {
            "titulo": "Omelete de queijo",
            "descricao": "Omelete macia com queijo, pronta em 5 minutos.",
            "ingredientes": ["ovo", "queijo", "manteiga", "sal", "salsa"],
            "passos": [
                "Bate 3 ovos com uma pitada de sal.",
                "Derrete a manteiga numa frigideira em lume médio e deita os ovos.",
                "Quando a base prender, põe o queijo e a salsa numa metade.",
                "Dobra ao meio e serve logo.",
            ],
        },
        "en": {
            "titulo": "Cheese omelette",
            "descricao": "A soft cheese omelette, ready in 5 minutes.",
            "ingredientes": ["egg", "cheese", "butter", "salt", "parsley"],
            "passos": [
                "Beat 3 eggs with a pinch of salt.",
                "Melt the butter in a pan over medium heat and pour in the eggs.",
                "Once the base sets, add cheese and parsley on one half.",
                "Fold over and serve right away.",
            ],
        },
    },
    {
        "principais": ["arroz"],
        "pt": {
            "titulo": "Arroz de tomate",
            "descricao": "O arroz de tomate português, malandrinho e aromático.",
            "ingredientes": ["arroz", "tomate", "cebola", "alho", "azeite", "sal", "salsa"],
            "passos": [
                "Refoga a cebola e o alho picados em azeite durante 5 min.",
                "Junta o tomate picado e deixa desfazer 5 min.",
                "Acrescenta o arroz e o triplo de água a ferver; tempera com sal.",
                "Coze 15 min em lume brando e termina com salsa picada.",
            ],
        },
        "en": {
            "titulo": "Portuguese tomato rice",
            "descricao": "Portugal's loose, aromatic tomato rice.",
            "ingredientes": ["rice", "tomato", "onion", "garlic", "olive oil", "salt", "parsley"],
            "passos": [
                "Sauté chopped onion and garlic in olive oil for 5 min.",
                "Add chopped tomato and cook 5 min until it breaks down.",
                "Add the rice and three times its volume of boiling water; season with salt.",
                "Simmer 15 min and finish with chopped parsley.",
            ],
        },
    },
    {
        "principais": ["tomate"],
        "pt": {
            "titulo": "Salada de tomate",
            "descricao": "Salada fresca de tomate e cebola com azeite.",
            "ingredientes": ["tomate", "cebola", "azeite", "sal"],
            "passos": [
                "Corta o tomate em rodelas e a cebola em meias-luas finas.",
                "Dispõe numa travessa e tempera com sal.",
                "Rega com azeite e deixa 5 min antes de servir.",
            ],
        },
        "en": {
            "titulo": "Tomato and onion salad",
            "descricao": "A fresh tomato and onion salad with olive oil.",
            "ingredientes": ["tomato", "onion", "olive oil", "salt"],
            "passos": [
                "Slice the tomato and cut the onion into thin half-moons.",
                "Arrange on a plate and season with salt.",
                "Drizzle with olive oil and rest 5 min before serving.",
            ],
        },
    },
    {
        "principais": ["mandioca"],
        "pt": {
            "titulo": "Mandioca frita",
            "descricao": "Mandioca cozida e depois frita, estaladiça por fora.",
            "ingredientes": ["mandioca", "óleo", "sal"],
            "passos": [
                "Descasca a mandioca, corta em toros e coze em água com sal 20 min, até ficar macia.",
                "Escorre, retira o fio central e corta em palitos.",
                "Frita em óleo quente até dourar e tempera com sal.",
            ],
        },
        "en": {
            "titulo": "Fried cassava",
            "descricao": "Boiled then fried cassava, crispy outside.",
            "ingredientes": ["cassava", "oil", "salt"],
            "passos": [
                "Peel the cassava, cut into chunks and boil in salted water 20 min until tender.",
                "Drain, remove the woody core and cut into sticks.",
                "Fry in hot oil until golden and season with salt.",
            ],
        },
    },
]
