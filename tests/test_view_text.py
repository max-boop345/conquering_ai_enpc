"""Tests de l'export texte de la vue joueur (B03) : grille ASCII + historique."""

import unittest

from demineur.game import Game
from demineur.view_text import view_to_text


class TestViewTexte(unittest.TestCase):
    def setUp(self):
        self.game = Game(width=5, height=5, mines_count=3, seed=4)
        self.game.reveal(0, 0)
        self.game.flag(4, 4)

    def test_format_compact(self):
        texte = view_to_text(self.game.view(), historique=[["reveal", 0, 0], ["flag", 4, 4]])
        lignes = texte.splitlines()
        # entête + 5 lignes de grille + historique
        self.assertTrue(any("5x5" in ligne for ligne in lignes))
        self.assertEqual(sum(1 for ligne in lignes
                       if len(ligne) == 5 and set(ligne) <= set(".F012345678")), 5)
        self.assertIn("reveal 0 0", texte)
        self.assertIn("flag 4 4", texte)

    def test_historique_vide_optionnel(self):
        texte = view_to_text(self.game.view())
        self.assertIn(".", texte)

    def test_etat_terminal_affiche(self):
        texte = view_to_text(self.game.view())
        self.assertIn("playing", texte)


if __name__ == "__main__":
    unittest.main()
