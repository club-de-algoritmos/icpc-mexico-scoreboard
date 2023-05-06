from icpc_mexico_scoreboard.rank_notifier import notify_rank_updates, notify_rank_updates_until_finished

if __name__ == "__main__":
    # notify_rank_updates_until_finished(
    #    "http://animeitor.naquadah.com.br/everything2.html?contest=Mexico&filter=teammx&sede=Mexico",
    #    "[IT Culiacan]|[UAS]|[FIMAZ]")
    notify_rank_updates_until_finished("https://score.icpcmexico.org", "IT Culiacan|UASinaloa|FIMAZ")
    # notify_rank_updates("https://score.icpcmexico.org/2022/primera_fecha/score.html", "IT Culiacan|UAS")
