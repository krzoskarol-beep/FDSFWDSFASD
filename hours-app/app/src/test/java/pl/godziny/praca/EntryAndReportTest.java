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
        String r = Report.build(week, w, 0, WorkMathTest.WAW);
        assertTrue(r, r.contains("Tydzień: 23.11 – 29.11.2026"));
        assertTrue(r, r.contains("Początek tygodnia: poniedziałek, 00:00"));
        assertTrue(r, r.contains("Stawka:      $34.00/h"));
        assertTrue(r, r.contains("Pn 23.11  08:00–16:30    8:30 h    $289.00"));
        assertTrue(r, r.contains("          17:00–18:00    1:00 h     $34.00"));
        assertTrue(r, r.contains("Wt 24.11  22:00–06:00    8:00 h    $272.00"));
        assertTrue(r, r.contains("Dni pracy:   2"));
        assertTrue(r, r.contains("Razem:       17:30 h (17.50 h)"));
        assertTrue(r, r.contains("DO WYPŁATY:  $595.00 brutto"));
        assertTrue(r, !r.contains("nadgodziny:"));
    }

    @Test public void reportMarksRunningShiftAndEmptyWeek() {
        long w = WorkMathTest.t(WorkMathTest.WAW, 2026, 11, 23, 0, 0);
        String r = Report.build(Collections.singletonList(new Entry(1, w + 8 * WorkMath.HOUR, 0)),
                w, w + 10 * WorkMath.HOUR, WorkMathTest.WAW);
        assertTrue(r, r.contains("08:00–teraz    2:00 h     $68.00  (w trakcie)"));
        assertTrue(Report.build(Collections.emptyList(), w, 0, WorkMathTest.WAW)
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

    @Test public void reportShowsBreakEditsAndNoOvertime() {
        long w = WorkMathTest.t(WorkMathTest.WAW, 2026, 11, 23, 0, 0);
        long h = WorkMath.HOUR, m = WorkMath.MINUTE;
        java.util.List<Entry> week = new java.util.ArrayList<>(WorkMathTest.week(42, 3400, 1));
        Entry first = week.get(0);   // Pn 06:00–16:00, poprawiony z zegara 06:07, przerwa 0:30
        week.set(0, new Entry(first.id, first.start, first.end + 30 * m, 30, 3400,
                first.start + 7 * m, first.end + 30 * m, false));
        String r = Report.build(week, w, 0, WorkMathTest.WAW);
        assertTrue(r, r.contains("[przerwa 0:30; poprawiono, zegar: 06:07–16:30]"));
        assertTrue(r, r.contains("Razem:       42:00 h (42.00 h)"));
        assertTrue(r, r.contains("DO WYPŁATY:  $1,428.00 brutto"));      // 42 h × $34, bez dopłat
        assertTrue(r, !r.toLowerCase().contains("nadgodzin") && !r.contains("FLSA") && !r.contains("Dopłata"));
        assertTrue(r, !r.contains("Czas liczony") && !r.contains("Przerwy odjęte"));
        assertTrue(r, r.trim().endsWith("DO WYPŁATY:  $1,428.00 brutto"));   // nic pod kwotą
    }

    @Test public void monthlyReportClipsToMonthAndGroupsWeeks() {
        java.util.TimeZone tz = WorkMathTest.WAW;
        long h = WorkMath.HOUR;
        long oct30 = WorkMathTest.t(tz, 2026, 10, 30, 8, 0);   // pt — poza listopadem
        long nov2 = WorkMathTest.t(tz, 2026, 11, 2, 8, 0);     // pn — tydzień 02.11
        long nov1 = WorkMathTest.t(tz, 2026, 11, 1, 9, 0);     // nd — tydzień 26.10–01.11 (przycięty)
        long nov30 = WorkMathTest.t(tz, 2026, 11, 30, 7, 0);   // pn — tydzień 30.11 (przycięty)
        long dec1 = WorkMathTest.t(tz, 2026, 12, 1, 7, 0);     // wt — poza listopadem
        java.util.List<Entry> all = Arrays.asList(
                new Entry(1, oct30, oct30 + 8 * h),
                new Entry(2, nov1, nov1 + 4 * h),
                new Entry(3, nov2, nov2 + 8 * h),
                new Entry(4, nov2 + 24 * h, nov2 + 24 * h + 8 * h + 30 * WorkMath.MINUTE),
                new Entry(5, nov30, nov30 + 10 * h),
                new Entry(6, dec1, dec1 + 8 * h));
        long m = Report.monthStart(WorkMathTest.t(tz, 2026, 11, 17, 12, 0), tz);
        assertEquals(WorkMathTest.t(tz, 2026, 11, 1, 0, 0), m);
        String r = Report.buildMonth(all, m, java.util.Calendar.MONDAY, 0, tz);
        assertTrue(r, r.contains("Miesiąc: listopad 2026 (01.11 – 30.11.2026)"));
        assertTrue(r, r.contains("Tydzień 01.11 – 01.11\nNd 01.11  09:00–13:00    4:00 h    $136.00"));
        assertTrue(r, r.contains("Tydzień 02.11 – 08.11\n"));
        assertTrue(r, r.contains("razem tygodnia: 16:30 h  $561.00"));
        assertTrue(r, r.contains("Tydzień 30.11 – 30.11\n"));
        assertTrue(r, !r.contains("30.10") && !r.contains("01.12"));        // spoza miesiąca
        assertTrue(r, r.contains("Dni pracy:   4"));
        assertTrue(r, r.contains("Razem:       30:30 h (30.50 h)"));
        assertTrue(r, r.contains("DO WYPŁATY:  $1,037.00 brutto"));          // 30.5 h × $34
        assertEquals("październik 2026", Report.monthLabel(Report.addMonths(m, -1, tz), tz));
        assertTrue(Report.buildMonth(all, Report.addMonths(m, -5, tz), java.util.Calendar.MONDAY, 0, tz)
                .contains("Brak wpisów w tym miesiącu."));
    }
}
