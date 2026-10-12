"""The journal is the revert path. It must survive everything."""


def test_record_then_read_back(journal):
    token = journal.record(
        tool="power.monitor_timeout", args={"minutes": 30},
        prior={"minutes": 10}, command="powercfg /change monitor-timeout-ac 30",
    )
    entry = journal.get(token)
    assert entry is not None
    assert entry.prior == {"minutes": 10}
    assert entry.args == {"minutes": 30}
    assert entry.undone is False


def test_last_undoable_is_the_most_recent(journal):
    journal.record("power.monitor_timeout", {"minutes": 20}, {"minutes": 10}, "a")
    second = journal.record("power.sleep_timeout", {"minutes": 60}, {"minutes": 30}, "b")
    assert journal.last_undoable().id == second


def test_undone_entries_are_skipped(journal):
    first = journal.record("power.monitor_timeout", {"minutes": 20}, {"minutes": 10}, "a")
    second = journal.record("power.sleep_timeout", {"minutes": 60}, {"minutes": 30}, "b")
    journal.mark_undone(second)
    assert journal.last_undoable().id == first
    journal.mark_undone(first)
    assert journal.last_undoable() is None


def test_nothing_to_undo_on_fresh_journal(journal):
    assert journal.last_undoable() is None


def test_marking_undone_preserves_all_entries(journal):
    ids = [
        journal.record("power.monitor_timeout", {"minutes": n}, {"minutes": n - 1}, "c")
        for n in (11, 12, 13)
    ]
    journal.mark_undone(ids[1])
    entries = list(journal.entries())
    assert [e.id for e in entries] == ids          # nothing deleted or reordered
    assert [e.undone for e in entries] == [False, True, False]


def test_corrupt_line_does_not_lose_the_rest(journal, capsys):
    good = journal.record("power.monitor_timeout", {"minutes": 20}, {"minutes": 10}, "a")
    with journal.path.open("a") as fh:
        fh.write("{ this is not json\n")
    also_good = journal.record("power.sleep_timeout", {"minutes": 60}, {"minutes": 30}, "b")

    ids = [e.id for e in journal.entries()]
    assert good in ids and also_good in ids
    assert "corrupt journal line" in capsys.readouterr().err


def test_undo_is_itself_recorded(journal):
    changed = journal.record("power.monitor_timeout", {"minutes": 20}, {"minutes": 10}, "a")
    journal.record_undo(changed, "power.monitor_timeout", "powercfg /change x 10")
    kinds = [e.kind for e in journal.entries()]
    assert kinds == ["change", "undo"]
