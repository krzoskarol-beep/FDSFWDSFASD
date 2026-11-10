package pl.gps.pozycja;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import android.content.Context;

import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;

import java.util.List;

@RunWith(AndroidJUnit4.class)
public class EventLogTest {

    private final Context context = ApplicationProvider.getApplicationContext();

    @Before
    public void setUp() {
        EventLog.clear(context);
    }

    @Test
    public void newestEntryIsFirst() {
        EventLog.log(context, "pierwszy");
        EventLog.log(context, "drugi");
        List<String> entries = EventLog.read(context);
        assertEquals(2, entries.size());
        assertTrue(entries.get(0).endsWith("drugi"));
        assertTrue(entries.get(1).endsWith("pierwszy"));
    }

    @Test
    public void multilineMessageStaysOneEntry() {
        EventLog.log(context, "a\nb");
        assertEquals(1, EventLog.read(context).size());
    }

    @Test
    public void logIsTrimmedButKeepsNewestEntries() {
        int total = EventLog.MAX_ENTRIES * 2;
        for (int i = 0; i < total; i++) {
            EventLog.log(context, "wpis numer " + i + " z dodatkowym tekstem, żeby linia była dłuższa");
        }
        List<String> entries = EventLog.read(context);
        assertTrue("za dużo wpisów: " + entries.size(), entries.size() <= EventLog.MAX_ENTRIES * 3 / 2);
        assertTrue(entries.size() >= EventLog.MAX_ENTRIES);
        assertTrue(entries.get(0).contains("wpis numer " + (total - 1) + " "));
    }
}
