import json
import tempfile
import unittest

from dome_world import BotState, SpatialLog, SwarmPhase, TelemetryStore, read_swarm
from dome_world.cli import main
from dome_world.notation import chain, released


def bot(name, vz, vx=0.0):
    return BotState(name, SwarmPhase.ACTING, (0.0, 0.0, 0.0), (vx, 0.0, vz))


class ReadingTests(unittest.TestCase):
    def test_all_still_is_rest(self):
        self.assertEqual(read_swarm([(0, 0, 0), (0, 0, 0)]).notation, "𝄐")

    def test_rise_alone_leaves_descent_open(self):
        r = read_swarm([(0, 0, 1), (0, 0, 0.5)])
        self.assertEqual(r.notation, "上//？下")
        self.assertIsNotNone(r.open_question)

    def test_descent_alone_leaves_rise_open(self):
        self.assertEqual(read_swarm([(0, 0, -1)]).notation, "？上//下")

    def test_balanced_loop_is_pattern_flow(self):
        r = read_swarm([(0, 0, 1), (0, 0, -1)])
        self.assertEqual(r.notation, "米(上//下)")
        self.assertIsNone(r.open_question)

    def test_unbalanced_pair_is_plain_pair(self):
        self.assertEqual(read_swarm([(0, 0, 2), (0, 0, -0.5)]).notation, "上//下")

    def test_rest_coexists_with_movement(self):
        self.assertEqual(read_swarm([(0, 0, 1), (0, 0, -1), (0, 0, 0)]).notation,
                         "米(上//下) · 𝄐")

    def test_level_movement_has_no_vertical_glyph(self):
        self.assertEqual(read_swarm([(1, 0, 0)]).notation, "")

    def test_release_and_chain(self):
        self.assertTrue(released(10.0, 12.0))
        self.assertFalse(released(10.0, 10.2))
        self.assertEqual(chain(["𝄐", "𝄐", "上//？下", "出", "米(上//下)"]),
                         "𝄐-上//？下-出-米(上//下)")


class LogTests(unittest.TestCase):
    def test_reading_survives_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            store = TelemetryStore(d)
            log = SpatialLog("t", [bot("a", 1), bot("b", -1)])
            store.write_log(log)
            loaded = store.read_log(log.log_id)
            self.assertEqual(loaded.metrics.reading.notation, "米(上//下)")
            with open(f"{d}/logs/{log.log_id}.json", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved["metrics"]["flow_core"]["glyphs"]["notation"], "米(上//下)")

    def test_markdown_tables_have_even_rows(self):
        md = SpatialLog("t", [bot("a", 1), bot("b", -1)]).to_markdown()
        for block in md.split("\n\n"):
            rows = [l for l in block.splitlines() if l.startswith("|")]
            if rows:
                widths = {row.count("|") for row in rows}
                self.assertEqual(len(widths), 1, block)

    def test_zero_bots_does_not_fall_back_to_saved_states(self):
        with tempfile.TemporaryDirectory() as d:
            store = TelemetryStore(d)
            store.write_state(bot("saved", 1))
            main(["--data-dir", d, "log", "--bots", "0"])
            logs = store.logs_in_order()
            self.assertEqual(len(logs[0].bot_states), 0)


if __name__ == "__main__":
    unittest.main()
