package pl.godziny.praca;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public class EntryAndReportTest {

    @Test public void codecRoundTripAndSkipsGarbage() {
        List<Entry> in = Arrays.asList(new Entry(1, 1000, 5000), new Entry(2, 6000, 0));
        List<Entry> out = Entry.decode(Entry.encode(in) + "zepsute\n3,9,1\n4,x,5\n", 3400);
        assertEquals(2, out.size());
        assertEquals(2, out.get(1).id);
        assertTrue(out.get(1).isRunning());
        assertEquals(5000, out.get(0).end);
        assertEquals(0, Entry.decode(null, 3400).size());
    }

    @Test public void weeklyReport() {
        long w = WorkMathTest.t(WorkMathTest.WAW, 2026, 11, 23, 0, 0);
        long h = WorkMath.HOUR;
        List<Entry> week = Arrays.asList(
                new Entry(1, w + 8 * h, w + 16 * h + 30 * WorkMath.MINUTE),     // Pn 8:30
                new Entry(2, w + 17 * h, w + 18 * h),                           // Pn 1:00
                new Entry(3, w + 24 * h + 22 * h, w + 48 * h + 6 * h));         // Wt 22–06 (przez północ)
        String r = Report.build(week, w, true, 0, WorkMathTest.WAW);
        assertTrue(r, r.contains("Tydzień: 23.11 – 29.11.2026"));
        assertTrue(r, r.contains("Początek tygodnia: poniedziałek, 00:00"));
        assertTrue(r, r.contains("Stawka regularna: $34.00/h"));
        assertTrue(r, r.contains("Pn 23.11  08:00–16:30    8:30 h    $289.00"));
        assertTrue(r, r.contains("          17:00–18:00    1:00 h     $34.00"));
        assertTrue(r, r.contains("Wt 24.11  22:00–06:00    8:00 h    $272.00"));
        assertTrue(r, r.contains("Dni pracy:        2"));
        assertTrue(r, r.contains("Razem:            17:30 h (17.50 h)"));
        assertTrue(r, r.contains("DO WYPŁATY:       $595.00 brutto"));
        assertTrue(r, !r.contains("nadgodziny:"));
    }

    @Test public void reportMarksRunningShiftAndEmptyWeek() {
        long w = WorkMathTest.t(WorkMathTest.WAW, 2026, 11, 23, 0, 0);
        String r = Report.build(Collections.singletonList(new Entry(1, w + 8 * WorkMath.HOUR, 0)),
                w, true, w + 10 * WorkMath.HOUR, WorkMathTest.WAW);
        assertTrue(r, r.contains("08:00–teraz    2:00 h     $68.00  (w trakcie)"));
        assertTrue(Report.build(Collections.emptyList(), w, true, 0, WorkMathTest.WAW)
                .contains("Brak wpisów"));
    }

    @Test public void legacyLinesKeepWorkingAndNewFieldsRoundTrip() {
        // Format z wersji 1.0–1.2: id,start,end — wczytuje się z bieżącą stawką i bez przerwy.
        Entry old = Entry.decode("5,1000,61000\n", 3600).get(0);
        assertEquals(3600, old.rateCents);
        assertEquals(0, old.breakMin);
        assertEquals(1000, old.origStart);
        assertTrue(!old.isEdited());

        Entry e = new Entry(9, 2000, 9000, 30, 3450, 1500, 9000, false);
        Entry back = Entry.decode(Entry.encode(Arrays.asList(e)), 1).get(0);
        assertEquals(30, back.breakMin);
        assertEquals(3450, back.rateCents);
        assertEquals(1500, back.origStart);
        assertTrue(back.isEdited());                    // początek różni się od zegara
        assertTrue(new Entry(1, 5, 9, 0, 1, 5, 9, true).isEdited());   // ręczny
        assertTrue(!new Entry(1, 5, 0, 0, 1, 5, 0, false).isEdited()); // trwa, bez zmian
        assertTrue(new Entry(1, 5, 9, 0, 1, 5, 0, false).isEdited());  // koniec ustawiony ręcznie
    }

    @Test public void reportShowsOvertimeBreakAndEdits() {
        long w = WorkMathTest.t(WorkMathTest.WAW, 2026, 11, 23, 0, 0);
        long h = WorkMath.HOUR, m = WorkMath.MINUTE;
        java.util.List<Entry> week = new java.util.ArrayList<>(WorkMathTest.week(42, 3400, 1));
        Entry first = week.get(0);   // Pn 06:00–16:00, poprawiony z zegara 06:07, przerwa 0:30
        week.set(0, new Entry(first.id, first.start, first.end + 30 * m, 30, 3400,
                first.start + 7 * m, first.end + 30 * m, false));
        String r = Report.build(week, w, true, 0, WorkMathTest.WAW);
        assertTrue(r, r.contains("[przerwa 0:30; poprawiono, zegar: 06:07–16:30]"));
        assertTrue(r, r.contains("  nadgodziny:     2:00 h (ponad 40 h, ×1.5)"));
        assertTrue(r, r.contains("Podstawa:         $1,428.00"));
        assertTrue(r, r.contains("Dopłata za nadg.: $34.00 (½ × $34.00 × 2.00 h)"));
        assertTrue(r, r.contains("DO WYPŁATY:       $1,462.00 brutto"));
        assertTrue(r, r.contains("Wpisy poprawione ręcznie"));
    }
}
