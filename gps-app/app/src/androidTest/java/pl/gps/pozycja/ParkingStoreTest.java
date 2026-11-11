package pl.gps.pozycja;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import android.content.Context;

import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;

import java.util.List;

@RunWith(AndroidJUnit4.class)
public class ParkingStoreTest {

    private final Context context = ApplicationProvider.getApplicationContext();
    private ParkingStore store;

    @Before
    public void setUp() {
        store = new ParkingStore(context);
        store.clear();
        store.clearHistory();
    }

    @Test
    public void emptyStoreReturnsNull() {
        assertNull(store.load());
    }

    @Test
    public void saveAndLoadKeepsFullPrecision() {
        store.save(new ParkingStore.Spot(52.2318381234567, 21.0059951234567, 7.5f, 1_700_000_000_000L,
                "poziom -2, sektor B"));
        ParkingStore.Spot s = new ParkingStore(context).load(); // nowa instancja = odczyt z pamięci
        assertNotNull(s);
        assertEquals(52.2318381234567, s.latitude, 0.0);
        assertEquals(21.0059951234567, s.longitude, 0.0);
        assertEquals(7.5f, s.accuracy, 0f);
        assertEquals(1_700_000_000_000L, s.savedAt);
        assertEquals("poziom -2, sektor B", s.note);
    }

    @Test
    public void clearRemovesSpot() {
        store.save(new ParkingStore.Spot(1, 2, 3, 4, ""));
        store.clear();
        assertNull(store.load());
    }

    @Test
    public void historyIsNewestFirstAndBounded() {
        for (int i = 0; i < ParkingStore.HISTORY_SIZE + 5; i++) {
            store.save(new ParkingStore.Spot(50 + i * 0.001, 20, 5, 1000L + i, "nr " + i));
        }
        List<ParkingStore.Spot> h = store.history();
        assertEquals(ParkingStore.HISTORY_SIZE, h.size());
        assertEquals("nr " + (ParkingStore.HISTORY_SIZE + 4), h.get(0).note);
    }

    @Test
    public void clearKeepsHistory_restoreDoesNotDuplicate() {
        ParkingStore.Spot a = new ParkingStore.Spot(50, 20, 5, 1000L, "A");
        ParkingStore.Spot b = new ParkingStore.Spot(51, 21, 5, 2000L, "B");
        store.save(a);
        store.save(b);
        store.clear();
        assertNull(store.load());
        assertEquals(2, store.history().size());

        store.restore(a);
        assertEquals("A", store.load().note);
        assertEquals(2, store.history().size());
    }

    @Test
    public void addressIsAttachedToMatchingSpotOnly() {
        ParkingStore.Spot a = new ParkingStore.Spot(50, 20, 5, 1000L, "A");
        store.save(a);
        store.save(new ParkingStore.Spot(51, 21, 5, 2000L, "B"));
        store.setAddress(1000L, "Floriańska 1, Kraków");   // adres dla starszego wpisu

        assertEquals("", store.load().address);            // aktualne (B) bez zmian
        boolean found = false;
        for (ParkingStore.Spot s : store.history()) {
            if (s.savedAt == 1000L) {
                assertEquals("Floriańska 1, Kraków", s.address);
                found = true;
            }
        }
        assertTrue(found);
    }

    @Test
    public void removeFromHistory() {
        store.save(new ParkingStore.Spot(50, 20, 5, 1000L, "A"));
        store.save(new ParkingStore.Spot(51, 21, 5, 2000L, "B"));
        store.removeFromHistory(1000L);
        assertEquals(1, store.history().size());
        assertEquals("B", store.history().get(0).note);
    }
}
