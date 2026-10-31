function genererNomAnime(prenom, age) {
    const partiesNom = [
        "Takahashi",
        "Fujimoto",
        "Yamamoto",
        "Kobayashi",
        "Hoshino",
        "Abe",
        "Tanaka",
        "Matsumoto",
        "Sasaki",
        "Inoue",
    ];

    // Un nombre calculé à partir du prénom : la somme des codes de ses lettres
    let nombre = 0;
    for (const lettre of prenom.toLowerCase()) {
        nombre += lettre.codePointAt(0);
    }

    const nom = partiesNom[nombre % partiesNom.length];

    let honorifique;
    if (age < 13) {
        honorifique = "-chan";
    } else if (age < 18) {
        honorifique = nombre % 2 === 0 ? "-kun" : "-san";
    } else if (age < 30) {
        honorifique = "-san";
    } else if (age < 50) {
        honorifique = "-sama";
    } else {
        honorifique = "-sensei";
    }

    return `${nom}${honorifique} ${prenom}`;
}

// Programme principal
const readline = require("readline").createInterface({
    input: process.stdin,
    output: process.stdout,
});

readline.question("Entrez votre vrai prénom : ", (prenom) => {
    readline.question("Entrez votre âge : ", (age) => {
        const nomAnime = genererNomAnime(prenom, parseInt(age));
        console.log(`Votre nom d'anime est : ${nomAnime}`);
        readline.close();
    });
});
