package pl.gps.pozycja;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import android.content.Context;
import android.content.res.XmlResourceParser;

import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.xmlpull.v1.XmlPullParser;

/** Skrót „Zapisz parking” musi wskazywać na tę aplikację (identyfikator zmienił się w 2.0). */
@RunWith(AndroidJUnit4.class)
public class ShortcutsTest {

    private static final String ANDROID_NS = "http://schemas.android.com/apk/res/android";

    @Test
    public void shortcutIntentTargetsThisApp() throws Exception {
        Context c = ApplicationProvider.getApplicationContext();
        int intents = 0;
        try (XmlResourceParser p = c.getResources().getXml(R.xml.shortcuts)) {
            for (int e = p.getEventType(); e != XmlPullParser.END_DOCUMENT; e = p.next()) {
                if (e == XmlPullParser.START_TAG && "intent".equals(p.getName())) {
                    intents++;
                    assertEquals(c.getPackageName(), p.getAttributeValue(ANDROID_NS, "targetPackage"));
                    assertEquals(MainActivity.class.getName(), p.getAttributeValue(ANDROID_NS, "targetClass"));
                    assertEquals(MainActivity.ACTION_SAVE_PARKING, p.getAttributeValue(ANDROID_NS, "action"));
                }
            }
        }
        assertTrue("brak skrótów", intents > 0);
    }
}
