

import random
from itertools import product


# ============================================================
#                       PARAMÈTRES
# ============================================================

LARGEUR = 16
HAUTEUR = 16
NOMBRE_MINES = 40


# ============================================================
#                       JEU DE DÉMINEUR
# ============================================================

class Demineur:

    def __init__(self, largeur, hauteur, nombre_mines):

        self.largeur = largeur
        self.hauteur = hauteur
        self.nombre_mines = nombre_mines

        # Emplacements secrets des mines
        self.mines = set()

        # Grille contenant les nombres
        self.grille = [
            [0 for _ in range(largeur)]
            for _ in range(hauteur)
        ]

        self.generer_grille()

    # --------------------------------------------------------
    # Génération de la grille
    # --------------------------------------------------------

    def generer_grille(self):

        toutes_les_cases = [
            (r, c)
            for r in range(self.hauteur)
            for c in range(self.largeur)
        ]

        # Placement aléatoire des mines
        self.mines = set(
            random.sample(
                toutes_les_cases,
                self.nombre_mines
            )
        )

        # Calcul des nombres autour de chaque mine
        for r, c in self.mines:

            for nr, nc in self.voisins(r, c):

                self.grille[nr][nc] += 1

    # --------------------------------------------------------
    # Cases voisines
    # --------------------------------------------------------

    def voisins(self, r, c):

        resultat = []

        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):

                if dr == 0 and dc == 0:
                    continue

                nr = r + dr
                nc = c + dc

                if (
                    0 <= nr < self.hauteur
                    and 0 <= nc < self.largeur
                ):
                    resultat.append((nr, nc))

        return resultat

    # --------------------------------------------------------
    # Clic sur une case
    # --------------------------------------------------------

    def cliquer(self, r, c):

        if (r, c) in self.mines:
            return "MINE"

        return self.grille[r][c]

    # --------------------------------------------------------
    # Affichage de la vraie grille
    # --------------------------------------------------------

    def afficher_grille_complete(self):

        print("\nGRILLE COMPLETE :")
        print()

        for r in range(self.hauteur):

            ligne = ""

            for c in range(self.largeur):

                if (r, c) in self.mines:
                    ligne += " 💣 "

                else:
                    ligne += f" {self.grille[r][c]} "

            print(ligne)

        print()


# ============================================================
#                       SOLVEUR
# ============================================================

class Solveur:

    def __init__(self, jeu):

        self.jeu = jeu

        self.largeur = jeu.largeur
        self.hauteur = jeu.hauteur

        # ----------------------------------------------------
        # Connaissance du solveur
        #
        # None = inconnue
        # int  = nombre découvert
        # "M"  = mine certaine
        # ----------------------------------------------------

        self.connaissance = [
            [None for _ in range(self.largeur)]
            for _ in range(self.hauteur)
        ]

        self.decouvertes = set()
        self.mines_trouvees = set()

    # ========================================================
    # VOISINS
    # ========================================================

    def voisins(self, r, c):

        return self.jeu.voisins(r, c)

    # ========================================================
    # ÉTAT DES VOISINS
    # ========================================================

    def analyser_voisins(self, r, c):

        inconnues = []
        mines = []

        for nr, nc in self.voisins(r, c):

            valeur = self.connaissance[nr][nc]

            if valeur is None:

                inconnues.append((nr, nc))

            elif valeur == "M":

                mines.append((nr, nc))

        return inconnues, mines

    # ========================================================
    # DÉCOUVRIR UNE CASE
    # ========================================================

    def decouvrir(self, r, c, raison=""):

        # Déjà connue
        if (r, c) in self.decouvertes:
            return True

        # Ne jamais cliquer sur un drapeau
        if (r, c) in self.mines_trouvees:
            return True

        resultat = self.jeu.cliquer(r, c)

        # Le solveur s'est trompé
        if resultat == "MINE":

            print()
            print("💥 BOOM !")
            print(
                f"Le solveur a cliqué sur une mine : "
                f"({r}, {c})"
            )
            print(f"Raison : {raison}")

            return False

        # Enregistrement du résultat
        self.connaissance[r][c] = resultat
        self.decouvertes.add((r, c))

        print(
            f"🔓 Case ({r},{c}) = {resultat}"
            f"   [{raison}]"
        )

        # ----------------------------------------------------
        # Si on découvre un 0, on ouvre automatiquement
        # les cases voisines.
        # ----------------------------------------------------

        if resultat == 0:

            for nr, nc in self.voisins(r, c):

                if (
                    (nr, nc) not in self.decouvertes
                    and (nr, nc) not in self.mines_trouvees
                ):

                    if not self.decouvrir(
                        nr,
                        nc,
                        "propagation d'un zéro"
                    ):
                        return False

        return True

    # ========================================================
    # POSER UN DRAPEAU
    # ========================================================

    def marquer_mine(self, r, c, raison=""):

        if (r, c) in self.decouvertes:
            return False

        if (r, c) in self.mines_trouvees:
            return False

        self.connaissance[r][c] = "M"
        self.mines_trouvees.add((r, c))

        print(
            f"🚩 Mine certaine en ({r},{c})"
            f"   [{raison}]"
        )

        return True

    # ========================================================
    # AFFICHAGE DE LA CONNAISSANCE DU SOLVEUR
    # ========================================================

    def afficher(self):

        print()

        for r in range(self.hauteur):

            ligne = ""

            for c in range(self.largeur):

                valeur = self.connaissance[r][c]

                if valeur is None:
                    ligne += " . "

                elif valeur == "M":
                    ligne += " F "

                else:
                    ligne += f" {valeur} "

            print(ligne)

        print()

    # ========================================================
    # STRATÉGIE 1
    # LOGIQUE DIRECTE
    #
    # Exemple :
    #
    # 1 F .
    #
    # Le "." est forcément sûr.
    #
    # Exemple :
    #
    # 1 . 
    #
    # si le 1 n'a qu'une case inconnue,
    # cette case est forcément une mine.
    # ========================================================

    def strategie_directe(self):

        action = False

        for r in range(self.hauteur):
            for c in range(self.largeur):

                valeur = self.connaissance[r][c]

                if not isinstance(valeur, int):
                    continue

                inconnues, mines = self.analyser_voisins(r, c)

                mines_restantes = valeur - len(mines)

                # ------------------------------------------------
                # Toutes les inconnues sont des mines
                # ------------------------------------------------

                if (
                    inconnues
                    and mines_restantes == len(inconnues)
                ):

                    for case in inconnues:

                        if self.marquer_mine(
                            *case,
                            raison=f"règle directe depuis ({r},{c})"
                        ):
                            action = True

                # ------------------------------------------------
                # Toutes les mines sont déjà trouvées
                # donc les inconnues sont sûres
                # ------------------------------------------------

                elif (
                    inconnues
                    and mines_restantes == 0
                ):

                    for case in inconnues:

                        if self.decouvrir(
                            *case,
                            raison=f"case sûre depuis ({r},{c})"
                        ):
                            action = True

        return action

    # ========================================================
    # CONSTRUIRE LES CONTRAINTES
    #
    # Une contrainte :
    #
    # {A, B, C} = 2
    #
    # signifie :
    # parmi A, B et C, il y a exactement 2 mines.
    # ========================================================

    def construire_contraintes(self):

        contraintes = []

        for r in range(self.hauteur):
            for c in range(self.largeur):

                valeur = self.connaissance[r][c]

                if not isinstance(valeur, int):
                    continue

                inconnues, mines = self.analyser_voisins(r, c)

                if not inconnues:
                    continue

                mines_restantes = valeur - len(mines)

                contraintes.append(
                    (
                        frozenset(inconnues),
                        mines_restantes
                    )
                )

        return contraintes

    # ========================================================
    # STRATÉGIE 2
    # SOUS-ENSEMBLES
    #
    # Exemple :
    #
    # A + B = 1
    # A + B + C = 2
    #
    # donc :
    #
    # C = 1
    #
    # C est une mine.
    #
    # Ou :
    #
    # A + B = 1
    # A + B + C = 1
    #
    # donc :
    #
    # C = 0
    #
    # C est sûre.
    # ========================================================

    def strategie_sous_ensembles(self):

        contraintes = self.construire_contraintes()

        action = False

        for cases_a, mines_a in contraintes:

            for cases_b, mines_b in contraintes:

                if cases_a == cases_b:
                    continue

                # A est inclus dans B
                if not cases_a.issubset(cases_b):
                    continue

                difference = cases_b - cases_a

                mines_difference = mines_b - mines_a

                if not difference:
                    continue

                # ------------------------------------------------
                # Toutes les cases de la différence sont des mines
                # ------------------------------------------------

                if mines_difference == len(difference):

                    for case in difference:

                        if self.marquer_mine(
                            *case,
                            raison="différence de contraintes"
                        ):
                            action = True

                # ------------------------------------------------
                # Aucune mine dans la différence
                # ------------------------------------------------

                elif mines_difference == 0:

                    for case in difference:

                        if self.decouvrir(
                            *case,
                            raison="différence de contraintes"
                        ):
                            action = True

        return action

    # ========================================================
    # STRATÉGIE 3
    # DÉCOMPTE GLOBAL
    # ========================================================

    def strategie_globale(self):

        inconnues = [
            (r, c)
            for r in range(self.hauteur)
            for c in range(self.largeur)
            if self.connaissance[r][c] is None
        ]

        mines_restantes = (
            self.jeu.nombre_mines
            - len(self.mines_trouvees)
        )

        action = False

        # ----------------------------------------------------
        # Toutes les cases restantes sont des mines
        # ----------------------------------------------------

        if (
            inconnues
            and mines_restantes == len(inconnues)
        ):

            for case in inconnues:

                if self.marquer_mine(
                    *case,
                    raison="décompte global"
                ):
                    action = True

        # ----------------------------------------------------
        # Toutes les mines ont été trouvées
        # ----------------------------------------------------

        elif (
            inconnues
            and mines_restantes == 0
        ):

            for case in inconnues:

                if self.decouvrir(
                    *case,
                    raison="plus aucune mine restante"
                ):
                    action = True

        return action

    # ========================================================
    # CASES FRONTIÈRES
    #
    # Ce sont les cases inconnues qui touchent au moins
    # une case déjà découverte.
    # ========================================================

    def frontiere(self):

        cases = set()

        for r in range(self.hauteur):
            for c in range(self.largeur):

                if not isinstance(
                    self.connaissance[r][c],
                    int
                ):
                    continue

                inconnues, _ = self.analyser_voisins(r, c)

                for case in inconnues:
                    cases.add(case)

        return cases

    # ========================================================
    # STRATÉGIE 4
    # CALCUL EXACT DES PROBABILITÉS
    #
    # On teste toutes les configurations possibles des mines
    # sur la frontière et on élimine celles qui contredisent
    # les chiffres connus.
    # ========================================================

    def probabilites_exactes(self):

        contraintes = self.construire_contraintes()

        if not contraintes:
            return {}

        frontier = sorted(self.frontiere())

        # ----------------------------------------------------
        # Si la frontière est trop grande, l'énumération
        # devient exponentielle.
        # ----------------------------------------------------

        if len(frontier) > 22:

            return self.probabilites_approximees()

        index = {
            case: i
            for i, case in enumerate(frontier)
        }

        configurations_valides = 0

        nombre_mines_par_case = {
            case: 0
            for case in frontier
        }

        # ----------------------------------------------------
        # Test de toutes les configurations
        # ----------------------------------------------------

        nombre_configurations = 2 ** len(frontier)

        for masque in range(nombre_configurations):

            valide = True

            # Vérification de chaque contrainte
            for cases, mines_requises in contraintes:

                nombre_mines = 0

                for case in cases:

                    position = index[case]

                    if masque & (1 << position):
                        nombre_mines += 1

                if nombre_mines != mines_requises:

                    valide = False
                    break

            if not valide:
                continue

            # Configuration compatible
            configurations_valides += 1

            for case in frontier:

                position = index[case]

                if masque & (1 << position):

                    nombre_mines_par_case[case] += 1

        # Aucune configuration possible
        if configurations_valides == 0:
            return {}

        # ----------------------------------------------------
        # Calcul des probabilités
        # ----------------------------------------------------

        probabilites = {}

        for case in frontier:

            probabilites[case] = (
                nombre_mines_par_case[case]
                / configurations_valides
            )

        return probabilites

    # ========================================================
    # PROBABILITÉS APPROXIMATIVES
    # ========================================================

    def probabilites_approximees(self):

        contraintes = self.construire_contraintes()

        probabilites = {}

        for cases, mines in contraintes:

            if not cases:
                continue

            p = mines / len(cases)

            for case in cases:

                if case not in probabilites:
                    probabilites[case] = []

                probabilites[case].append(p)

        resultat = {}

        for case, valeurs in probabilites.items():

            resultat[case] = sum(valeurs) / len(valeurs)

        return resultat

    # ========================================================
    # STRATÉGIE 5
    # CHOIX PROBABILISTE
    # ========================================================

    def strategie_probabiliste(self):

        probabilites = self.probabilites_exactes()

        if not probabilites:
            return False

        # Case ayant la plus faible probabilité d'être une mine
        case = min(
            probabilites,
            key=probabilites.get
        )

        probabilite = probabilites[case]

        r, c = case

        print()
        print("🎲 Aucune déduction certaine.")
        print(
            f"Case choisie : ({r},{c})"
        )
        print(
            f"Probabilité d'être une mine : "
            f"{probabilite:.2%}"
        )

        # Si 0 %, on sait en réalité qu'elle est sûre
        if probabilite == 0:

            return self.decouvrir(
                r,
                c,
                "probabilité exacte = 0 %"
            )

        # Si 100 %, on peut la marquer
        if probabilite == 1:

            return self.marquer_mine(
                r,
                c,
                "probabilité exacte = 100 %"
            )

        # Sinon, il faut prendre un risque
        return self.decouvrir(
            r,
            c,
            f"choix probabiliste ({probabilite:.2%})"
        )

    # ========================================================
    # VICTOIRE
    # ========================================================

    def victoire(self):

        nombre_cases_sures = (
            self.largeur * self.hauteur
            - self.jeu.nombre_mines
        )

        return len(self.decouvertes) >= nombre_cases_sures

    # ========================================================
    # RÉSOLUTION COMPLÈTE
    # ========================================================

    def resoudre(self):

        print()
        print("=" * 70)
        print("                 DÉBUT DE LA RÉSOLUTION")
        print("=" * 70)

        # ----------------------------------------------------
        # Premier clic
        # ----------------------------------------------------

        premier_clic = (
            self.hauteur // 2,
            self.largeur // 2
        )

        print(
            f"\n🚀 Premier clic : {premier_clic}"
        )

        if not self.decouvrir(
            *premier_clic,
            raison="premier clic"
        ):
            return False

        tour = 0

        # ----------------------------------------------------
        # Boucle de résolution
        # ----------------------------------------------------

        while not self.victoire():

            tour += 1

            print()
            print("-" * 70)
            print(f"TOUR {tour}")
            print("-" * 70)

            self.afficher()

            # =================================================
            # 1. LOGIQUE DIRECTE
            # =================================================

            if self.strategie_directe():
                continue

            if self.victoire():
                break

            # =================================================
            # 2. SOUS-ENSEMBLES
            # =================================================

            if self.strategie_sous_ensembles():
                continue

            if self.victoire():
                break

            # =================================================
            # 3. DÉCOMPTE GLOBAL
            # =================================================

            if self.strategie_globale():
                continue

            if self.victoire():
                break

            # =================================================
            # 4. PROBABILITÉS
            # =================================================

            if not self.strategie_probabiliste():

                print()
                print(
                    "❌ Impossible de poursuivre."
                )

                break

        # ----------------------------------------------------
        # Résultat
        # ----------------------------------------------------

        print()
        print("=" * 70)

        if self.victoire():

            print("🎉 VICTOIRE !")
            print(
                f"Cases découvertes : "
                f"{len(self.decouvertes)}"
            )
            print(
                f"Mines trouvées : "
                f"{len(self.mines_trouvees)} / "
                f"{self.jeu.nombre_mines}"
            )

        else:

            print("💥 LE SOLVEUR A PERDU OU EST BLOQUÉ.")

        print("=" * 70)

        self.afficher()

        return self.victoire()


# ============================================================
#                    PROGRAMME PRINCIPAL
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # 1. GÉNÉRATION DE LA GRILLE
    # --------------------------------------------------------

    print("=" * 70)
    print("                  GÉNÉRATION")
    print("=" * 70)

    jeu = Demineur(
        largeur=LARGEUR,
        hauteur=HAUTEUR,
        nombre_mines=NOMBRE_MINES
    )

    print(
        f"\nGrille : {LARGEUR} x {HAUTEUR}"
    )

    print(
        f"Nombre de mines : {NOMBRE_MINES}"
    )

    # --------------------------------------------------------
    # Affichage de la grille réelle
    # --------------------------------------------------------
    #
    # Tu peux commenter cette ligne si tu veux que le solveur
    # soit réellement "aveugle" visuellement.
    #
    # Le solveur lui-même n'utilise JAMAIS cette information.
    #

    jeu.afficher_grille_complete()

    # --------------------------------------------------------
    # 2. CRÉATION DU SOLVEUR
    # --------------------------------------------------------

    solveur = Solveur(jeu)

    # --------------------------------------------------------
    # 3. RÉSOLUTION
    # --------------------------------------------------------

    solveur.resoudre()
