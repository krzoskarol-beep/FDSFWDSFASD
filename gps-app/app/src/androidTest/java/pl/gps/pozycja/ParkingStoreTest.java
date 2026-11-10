package pl.gps.pozycja;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;

import android.content.Context;

import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(AndroidJUnit4.class)
public class ParkingStoreTest {

    private final Context context = ApplicationProvider.getApplicationContext();
    private ParkingStore store;

    @Before
    public void setUp() {
        store = new ParkingStore(context);
        store.clear();
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
}
