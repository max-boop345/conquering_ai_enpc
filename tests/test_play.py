"""Tests du rendu texte et du jeu au clavier (A14, F02)."""

import io
import unittest

from demineur.game import Game, GameState
from demineur.play import run
from demineur.render import render_view


class TestRenduTexte(unittest.TestCase):
    def setUp(self):
        self.game = Game(width=5, height=5, mines_count=3, seed=4)
        self.game.reveal(0, 0)
        self.game.flag(4, 4)

    def test_largeur_du_rendu(self):
        texte = render_view(self.game.view())
        lignes = texte.splitlines()
        self.assertEqual(len(lignes), 5)
        self.assertTrue(all(len(l) == 5 for l in lignes))

    def test_symboles(self):
        texte = render_view(self.game.view())
        self.assertIn("F", texte)  # drapeau
        self.assertIn(".", texte)  # cachée
        self.assertIn("0", texte)  # révélée
        # aucun indice sur les mines cachées: seuls . F et chiffres apparaissent
        self.assertTrue(set(texte) <= set(".F012345678\n"))


class TestPlayClavier(unittest.TestCase):
    """A14 : partie jouable par commandes texte (testée avec flux simulé)."""

    def test_partie_complete(self):
        entree = io.StringIO("r 0 0\nq\n")
        sortie = io.StringIO()
        jeu, journal = run(
            Game(width=5, height=5, mines_count=3, seed=4),
            input_stream=entree,
            output_stream=sortie,
        )
        self.assertEqual(len(journal), 1)
        self.assertTrue(len(jeu.revealed) > 0)
        self.assertIn("mines restantes", sortie.getvalue())

    def test_commande_invalide_ne_plante_pas(self):
        entree = io.StringIO("xxx\nr a b\nq\n")
        sortie = io.StringIO()
        _, journal = run(
            Game(width=5, height=5, mines_count=3, seed=4),
            input_stream=entree,
            output_stream=sortie,
        )
        self.assertEqual(journal, [])
        self.assertIn("invalide", sortie.getvalue().lower())

    def test_coup_illegal_message_erreur(self):
        entree = io.StringIO("r 0 0\nr 0 0\nq\n")
        sortie = io.StringIO()
        _, journal = run(
            Game(width=5, height=5, mines_count=3, seed=4),
            input_stream=entree,
            output_stream=sortie,
        )
        self.assertEqual(len(journal), 1)
        self.assertIn("erreur", sortie.getvalue().lower())

    def test_victoire_detectee(self):
        # 3x3, 1 mine en seed=0 : le test construit les coups en évitant la mine connue
        jeu_ref = Game(width=3, height=3, mines_count=1, seed=0)
        jeu_ref.reveal(0, 0)
        mine = next(iter(jeu_ref.board.mines))
        sur = [f"r {x} {y}" for y in range(3) for x in range(3)
               if (x, y) not in jeu_ref.revealed and (x, y) != mine]
        entree = io.StringIO("\n".join(sur) + "\nq\n")
        jeu, _ = run(jeu_ref, input_stream=entree, output_stream=io.StringIO())
        self.assertEqual(jeu.state, GameState.WON)


if __name__ == "__main__":
    unittest.main()
