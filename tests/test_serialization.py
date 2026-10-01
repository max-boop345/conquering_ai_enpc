"""Tests de sérialisation JSON versionnée (A15) et presets (A16)."""

import json
import unittest

from demineur.game import Game
from demineur.presets import get_preset, list_presets
from demineur.serialization import game_from_json, game_to_json
from demineur.view import view_from_json


class TestSerialisation(unittest.TestCase):
    def _partie(self):
        game = Game(width=5, height=5, mines_count=3, seed=11)
        game.reveal(0, 0)
        game.flag(3, 3)
        return game

    def test_round_trip_etat_complet(self):
        game = self._partie()
        data = game_to_json(game)
        restored = game_from_json(data)
        self.assertEqual(restored.board.mines, game.board.mines)
        self.assertEqual(restored.revealed, game.revealed)
        self.assertEqual(restored.flags, game.flags)
        self.assertEqual(restored.state, game.state)

    def test_version_dans_le_format(self):
        data = game_to_json(self._partie())
        self.assertEqual(data["version"], 1)

    def test_version_future_refusee(self):
        data = game_to_json(self._partie())
        data["version"] = 99
        with self.assertRaises(ValueError):
            game_from_json(data)

    def test_champ_manquant_refuse(self):
        data = game_to_json(self._partie())
        del data["mines"]
        with self.assertRaises(ValueError):
            game_from_json(data)

    def test_json_serialisable(self):
        # le dict doit être dumpable en texte sans erreur
        texte = json.dumps(game_to_json(self._partie()))
        restored = game_from_json(json.loads(texte))
        self.assertEqual(restored.mines_count, 3)

    def test_vue_json_ne_contient_pas_les_mines(self):
        data = self._partie().view().to_json()
        texte = json.dumps(data)
        self.assertNotIn("is_mine", texte)
        self.assertNotIn("mines", data.keys())  # aucune liste de positions de mines
        self.assertIn("mines_count", data)  # seul le total est public

    def test_round_trip_vue(self):
        view = self._partie().view()
        restored = view_from_json(view.to_json())
        self.assertEqual(restored.to_json(), view.to_json())

    def test_partie_pas_commencee(self):
        # aucune mine placée: la sérialisation doit rester possible (mines vides)
        game = Game(width=4, height=4, mines_count=2, seed=0)
        data = game_to_json(game)
        self.assertEqual(data["mines"], [])
        restored = game_from_json(data)
        self.assertIsNone(restored.board)


class TestPresets(unittest.TestCase):
    """A16 : presets de difficulté standard."""

    def test_presets_standard(self):
        self.assertEqual(get_preset("beginner").shape, (9, 9, 10))
        self.assertEqual(get_preset("intermediate").shape, (16, 16, 40))
        self.assertEqual(get_preset("expert").shape, (30, 16, 99))

    def test_preset_attributs(self):
        p = get_preset("expert")
        self.assertEqual(p.width, 30)
        self.assertEqual(p.height, 16)
        self.assertEqual(p.mines, 99)

    def test_liste_presets(self):
        self.assertEqual(set(list_presets()), {"beginner", "intermediate", "expert"})

    def test_preset_inconnu_refuse(self):
        with self.assertRaises(ValueError):
            get_preset("impossible")

    def test_preset_insensible_casse(self):
        self.assertEqual(get_preset("Beginner").name, "beginner")


if __name__ == "__main__":
    unittest.main()
