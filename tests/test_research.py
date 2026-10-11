import copy
import unittest

from src.research.core import FEATURES, Random, benchmark, build_features, cluster_interval, ranks, spearman


def game_snapshot(length=35):
    columns = ["s", "tid", "tn", "ta", "gn", "gd", "rd", "ord", "drd", "ad", "td", "pd", "tpad", "ftad", "w"]
    rows = [["2020-21", 1, "Test team", "TST", i, f"2021-01-{min(i,28):02}",
             -2, -1, -1, 3, -2, i, 2, 3, int(i % 3 != 0)] for i in range(1, length+1)]
    return dict(columns=columns, rows=rows)


class FeaturesTest(unittest.TestCase):
    def test_later_games_cannot_change_early_signal(self):
        payload = game_snapshot()
        original, _ = build_features(payload)
        changed = copy.deepcopy(payload)
        for row in changed["rows"][20:]:
            row[changed["columns"].index("rd")] = 500
            row[changed["columns"].index("pd")] = 1000
        updated, _ = build_features(changed)
        early = next(row for row in original if row["checkpoint"] == 20 and row["horizon"] == "remaining")
        later = next(row for row in updated if row["checkpoint"] == 20 and row["horizon"] == "remaining")
        for feature in FEATURES:
            self.assertEqual(early[feature], later[feature])
        self.assertNotEqual(early["future_point_diff"], later["future_point_diff"])
        self.assertEqual(early["future_games"], 15)
        self.assertEqual(early["future_point_diff"], sum(range(21,36))/15)

    def test_missing_metric_is_unknown_and_fixed_future_must_be_complete(self):
        payload = game_snapshot(25)
        payload["rows"][0][payload["columns"].index("rd")] = None
        rows, audit = build_features(payload)
        row = next(row for row in rows if row["checkpoint"] == 20 and row["horizon"] == "remaining")
        self.assertIsNone(row["rebound_diff"])
        self.assertIsNone(row["rebound_losses"])
        self.assertFalse(any(row["checkpoint"] == 20 and row["horizon"] == "next_10" for row in rows))
        self.assertEqual(next(a for a in audit if a["checkpoint"] == 20 and a["horizon"] == "next_10")["excluded_future"], 1)

    def test_missing_game_and_duplicates_are_not_silently_accepted(self):
        payload = game_snapshot()
        payload["rows"].pop(3)
        rows, _ = build_features(payload)
        self.assertEqual(rows, [])
        payload = game_snapshot()
        payload["rows"].append(payload["rows"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            build_features(payload)


def model_rows():
    rows = []
    for year in range(2000,2010):
        for team in range(12):
            wp=(team+1)/14; pd=team%5-2+(year-2000)*.1; reb=team%3-1
            rows.append(dict(season=f"{year}-{(year+1)%100:02}",team_id=team,
                             early_win_pct=wp,point_diff=pd,rebound_diff=reb,
                             future_win_pct=.2+.4*wp+.02*pd+.04*reb))
    return rows


class StatisticsTest(unittest.TestCase):
    def test_ties_and_constants(self):
        self.assertEqual(ranks([5,1,1,9]).tolist(), [3,1.5,1.5,4])
        self.assertAlmostEqual(spearman([1,2,3,4], [20,30,40,50]), 1)
        self.assertIsNone(spearman([1,1,1], [1,2,3]))
        self.assertIsNone(spearman([1,2], [1,2]))

    def test_season_resampling_is_seeded_and_requires_enough_clusters(self):
        rows=model_rows()
        a=cluster_interval(rows,"rebound_diff","future_win_pct",100)
        self.assertEqual(a,cluster_interval(rows,"rebound_diff","future_win_pct",100))
        self.assertIsNone(cluster_interval(rows[:12],"rebound_diff","future_win_pct",100))

    def test_later_targets_never_affect_fit_and_samples_are_shared(self):
        rows=model_rows(); rows[0]["rebound_diff"]=None
        a=benchmark(rows,"future_win_pct","2006-07",["rebound_diff"])
        self.assertEqual(a["earlier_n"],71)
        self.assertEqual(a["later_n"],48)
        self.assertEqual(a["excluded"],1)
        altered=copy.deepcopy(rows)
        for row in altered:
            if row["season"] >= "2006-07": row["future_win_pct"] += 100
        b=benchmark(altered,"future_win_pct","2006-07",["rebound_diff"])
        self.assertEqual([p["augmented"] for p in a["predictions"]], [p["augmented"] for p in b["predictions"]])
        self.assertLess(a["models"][2]["mae"], a["models"][1]["mae"])
        self.assertGreater(b["models"][2]["mae"],90)

    def test_selected_baseline_feature_adds_no_new_information(self):
        model=benchmark(model_rows(),"future_win_pct","2006-07",["point_diff"])
        self.assertEqual(model["added"],[])
        self.assertEqual(model["mae_improvement"],0)


if __name__ == "__main__": unittest.main()
