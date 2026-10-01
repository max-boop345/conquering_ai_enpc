"""Tests des actions (B02) et de leur parsing strict (B04)."""

import unittest

from demineur.actions import (
    Action,
    Flag,
    GiveUp,
    Reveal,
    Unflag,
    action_from_json,
    action_from_text,
    action_to_json,
    action_to_text,
)


class TestActions(unittest.TestCase):
    """B02 : type Action — Reveal | Flag | Unflag | GiveUp."""

    def test_action_immuable(self):
        a = Reveal(1, 2)
        with self.assertRaises(Exception):
            a.x = 3

    def test_egalite_structuelle(self):
        self.assertEqual(Reveal(1, 2), Reveal(1, 2))
        self.assertNotEqual(Reveal(1, 2), Reveal(1, 3))
        self.assertNotEqual(Reveal(1, 2), Flag(1, 2))
        self.assertIsInstance(Reveal(1, 2), Action)


class TestSerialisationActions(unittest.TestCase):
    """B04 : parsing depuis la forme sérialisée, validation stricte."""

    def test_round_trip_texte(self):
        for action in [Reveal(3, 4), Flag(0, 0), Unflag(8, 2), GiveUp("aucun coup légal")]:
            self.assertEqual(action_from_text(action_to_text(action)), action)

    def test_round_trip_json(self):
        for action in [Reveal(3, 4), Flag(0, 0), Unflag(8, 2), GiveUp("boucle")]:
            self.assertEqual(action_from_json(action_to_json(action)), action)

    def test_texte_valide(self):
        self.assertEqual(action_from_text("reveal 3 4"), Reveal(3, 4))
        self.assertEqual(action_from_text("flag 0 0"), Flag(0, 0))
        self.assertEqual(action_from_text("unflag 1 2"), Unflag(1, 2))

    def test_texte_invalide(self):
        for texte in [
            "reveal",            # arguments manquants
            "reveal 1",          # un seul argument
            "reveal a b",        # pas des entiers
            "reveal 1 2 3",      # trop d'arguments
            "dance 1 2",         # kind inconnu
            "REVEAL 1 2",        # casse non tolérée
            "reveal 1.5 2",     # pas des entiers
            "",                  # vide
        ]:
            with self.assertRaises(ValueError):
                action_from_text(texte)

    def test_json_invalide(self):
        for data in [
            {},
            {"kind": "reveal"},
            {"kind": "reveal", "x": 1, "y": 2, "extra": 3},
            {"kind": "dance", "x": 1, "y": 2},
            {"kind": "reveal", "x": "a", "y": 2},
            {"kind": "giveup"},
        ]:
            with self.assertRaises(ValueError):
                action_from_json(data)


if __name__ == "__main__":
    unittest.main()
