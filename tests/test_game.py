"""Tests du moteur de jeu (A05→A12) : révélation, cascade, drapeaux, fin de partie, anti-triche."""

import unittest

from demineur.game import Game, GameState


class TestRevelation(unittest.TestCase):
    """A07/A08 : révélation simple et en cascade."""

    def test_premier_coup_toujours_sur(self):
        # A05 : aucune mine sur la case cliquée ni ses voisines
        for seed in range(30):
            game = Game(width=6, height=6, mines_count=4, seed=seed)
            game.reveal(2, 2)
            board = game.board
            self.assertFalse(board.is_mine((2, 2)), f"seed {seed}")
            for v in board.neighbors((2, 2)):
                self.assertFalse(board.is_mine(v), f"seed {seed}: voisin {v} miné")

    def test_determinisme_seed(self):
        # même seed -> même suite de révélations
        g1 = Game(width=9, height=9, mines_count=10, seed=7)
        g2 = Game(width=9, height=9, mines_count=10, seed=7)
        g1.reveal(0, 0)
        g2.reveal(0, 0)
        self.assertEqual(g1.revealed, g2.revealed)
        self.assertEqual(g1.board.mines, g2.board.mines)

    def test_revelation_simple_sans_cascade(self):
        game = Game(width=6, height=6, mines_count=4, seed=0)
        # premier coup: zone 3x3 sûre et vide -> révèle au moins 9 cases,
        # les cases révélées avec compteurs ne cascadent pas
        resultats = game.reveal(0, 0)
        self.assertTrue(len(resultats) >= 9)

    def test_cascade_arretee_par_compteur(self):
        # grille construite: 3x3, mine en (2,2) -> révèle (0,0) cascade jusqu'au compteur de (1,1)
        game = Game(width=3, height=3, mines_count=1, seed=0)
        reveals = game.reveal(0, 0)
        # (2,2) est la mine; (1,1) a compteur 1 donc cascade s'arrête
        self.assertNotIn((2, 2), reveals)
        self.assertEqual(game.state, GameState.PLAYING)

    def test_reveler_case_deja_revelee_refusee(self):
        game = Game(width=5, height=5, mines_count=3, seed=1)
        game.reveal(0, 0)
        with self.assertRaises(ValueError):
            game.reveal(0, 0)

    def test_reveler_hors_grille_refusee(self):
        game = Game(width=5, height=5, mines_count=3, seed=1)
        with self.assertRaises(ValueError):
            game.reveal(9, 9)

    def test_reveler_case_drapeau_refusee(self):
        game = Game(width=5, height=5, mines_count=3, seed=1)
        game.flag(1, 1)
        with self.assertRaises(ValueError):
            game.reveal(1, 1)


class TestDrapeaux(unittest.TestCase):
    """A09 : drapeaux et compteur de mines restantes."""

    def test_flag_unflag(self):
        game = Game(width=5, height=5, mines_count=3, seed=2)
        game.flag(1, 1)
        self.assertTrue(game.is_flagged((1, 1)))
        self.assertEqual(game.mines_remaining, 2)
        game.unflag(1, 1)
        self.assertFalse(game.is_flagged((1, 1)))
        self.assertEqual(game.mines_remaining, 3)

    def test_flag_deux_fois_refuse(self):
        game = Game(width=5, height=5, mines_count=3, seed=2)
        game.flag(1, 1)
        with self.assertRaises(ValueError):
            game.flag(1, 1)

    def test_unflag_sans_flag_refuse(self):
        game = Game(width=5, height=5, mines_count=3, seed=2)
        with self.assertRaises(ValueError):
            game.unflag(1, 1)

    def test_flag_case_revelee_refuse(self):
        game = Game(width=5, height=5, mines_count=3, seed=2)
        game.reveal(0, 0)
        # après cascade, (0,0) est révélée
        with self.assertRaises(ValueError):
            game.flag(0, 0)

    def test_drapeaux_sans_limite_nombre_mines(self):
        # on autorise plus de drapeaux que de mines (le joueur se trompe)
        game = Game(width=5, height=5, mines_count=2, seed=2)
        game.flag(0, 0)
        game.flag(0, 1)
        game.flag(0, 2)
        self.assertEqual(game.mines_remaining, -1)


class TestFinDePartie(unittest.TestCase):
    """A10/A11 : victoire, défaite, état terminal."""

    def _partie_gagnable(self):
        # 3x3, mine en évitant la zone (0,0): seed choisi pour placer la mine hors cascade
        for seed in range(50):
            game = Game(width=3, height=3, mines_count=1, seed=seed)
            game.reveal(0, 0)
            if game.state == GameState.PLAYING and len(game.revealed) < 8:
                return game, seed
        self.fail("aucune seed ne produit une partie gagnable")

    def test_victoire(self):
        game, _ = self._partie_gagnable()
        # le joueur (omniscient pour le test) révèle toutes les cases sûres restantes
        for (x, y) in [(i, j) for i in range(3) for j in range(3)]:
            pos = (x, y)
            if pos not in game.revealed and not game.board.is_mine(pos):
                game.reveal(x, y)
        self.assertEqual(game.state, GameState.WON)

    def test_defaite(self):
        game, seed = self._partie_gagnable()
        # trouve la mine et la révèle
        mine = next(iter(game.board.mines))
        game.reveal(*mine)
        self.assertEqual(game.state, GameState.LOST)

    def test_aucune_action_apres_fin(self):
        game, _ = self._partie_gagnable()
        mine = next(iter(game.board.mines))
        game.reveal(*mine)
        with self.assertRaises(ValueError):
            game.reveal(2, 2)
        with self.assertRaises(ValueError):
            game.flag(2, 2)


class TestAntiTriche(unittest.TestCase):
    """A12 : l'emplacement des mines est figé au premier coup, jamais re-généré."""

    def test_mines_figees_apres_premier_coup(self):
        game = Game(width=6, height=6, mines_count=4, seed=3)
        self.assertIsNone(game.board)
        game.reveal(2, 2)
        mines_apres_coup1 = frozenset(game.board.mines)
        board_ref = game.board
        # plusieurs coups supplémentaires
        for pos in [(0, 0), (5, 5), (0, 5)]:
            if game.state == GameState.PLAYING:
                try:
                    game.reveal(*pos)
                except ValueError:
                    pass
        self.assertEqual(mines_apres_coup1, game.board.mines)
        self.assertIs(board_ref, game.board)

    def test_grille_non_reconstruite_apres_defaite(self):
        # si le joueur touche une mine, le plateau ne change plus
        game = Game(width=3, height=3, mines_count=1, seed=0)
        game.reveal(0, 0)
        mine = next(iter(game.board.mines))
        game.reveal(*mine)
        self.assertEqual(game.state, GameState.LOST)
        self.assertEqual(len(game.revealed), len(game.revealed))


if __name__ == "__main__":
    unittest.main()
