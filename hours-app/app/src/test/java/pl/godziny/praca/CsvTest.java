package pl.godziny.praca;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.Arrays;
import java.util.List;

public class CsvTest {

    private static final long H = WorkMath.HOUR, M = WorkMath.MINUTE;

    private static List<Entry> sample() {
        long w = WorkMathTest.t(WorkMathTest.WAW, 2026, 11, 23, 0, 0);
        return Arrays.asList(
                new Entry(1, w + 8 * H, w + 16 * H + 30 * M, 30, 3400, w + 8 * H + 4 * M, w + 16 * H + 30 * M, false),
                new Entry(2, w + 32 * H, w + 40 * H, 0, 3600, w + 32 * H, w + 40 * H, true),
                new Entry(3, w + 56 * H, 0, 0, 3400, w + 56 * H, 0, false));
    }

    @Test public void exportIsReadableAndRoundTrips() {
        long now = WorkMathTest.t(WorkMathTest.WAW, 2026, 11, 25, 10, 15);
        String csv = Csv.export(sample(), now, WorkMathTest.WAW);
        String[] lines = csv.split("\n");
        assertEquals(4, lines.length);
        assertTrue(lines[0].startsWith("data,dzien,poczatek,koniec,przerwa_min,minuty_platne"));
        // 08:00–16:30 minus 30 min przerwy = 480 min = 8.00 h × $34 = $272.00, poprawiony (zegar 08:04)
        assertTrue(lines[1], lines[1].startsWith("2026-11-23,Pn,08:00,16:30,30,480,8.00,34.00,272.00,zegar+poprawka,08:04,16:30,1,"));
        assertTrue(lines[2], lines[2].startsWith("2026-11-24,Wt,08:00,16:00,0,480,8.00,36.00,288.00,reczny,,,2,"));
        assertTrue(lines[3], lines[3].startsWith("2026-11-25,Śr,08:00,,0,135,2.25,34.00,76.50,zegar,08:00,,3,"));

        Csv.Result r = Csv.parse("\uFEFF" + csv.replace("\n", "\r\n"));
        assertNull(r.error);
        assertEquals(Entry.encode(sample()), Entry.encode(r.entries));
    }

    @Test public void rejectsForeignOrBrokenFiles() {
        assertNotNull(Csv.parse("").error);
        assertNotNull(Csv.parse("a,b,c\n1,2,3\n").error);
        String good = Csv.export(sample(), 0, WorkMathTest.WAW);
        String dupId = good + good.split("\n")[1] + "\n";
        assertTrue(Csv.parse(dupId).error.contains("powtórzony"));
        String broken = good.replace(",34.00,272.00,", ",abc,272.00,");
        assertTrue(Csv.parse(broken).error.contains("Wiersz 2"));
    }
}
