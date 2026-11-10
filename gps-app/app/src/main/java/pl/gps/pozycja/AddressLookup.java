package pl.gps.pozycja;

import android.app.NotificationManager;
import android.content.Context;
import android.location.Address;
import android.location.Geocoder;
import android.os.Build;
import android.service.notification.StatusBarNotification;

import java.io.IOException;
import java.util.List;
import java.util.Locale;

/**
 * Zamienia współrzędne zapisanego miejsca na adres („Marszałkowska 10, Warszawa”).
 * Korzysta z systemowego Geocodera: nie wymaga klucza API, a zapytanie sieciowe
 * wykonuje system. Bez internetu adres po prostu się nie pojawi.
 */
final class AddressLookup {

    private AddressLookup() { }

    /**
     * Ustala adres w tle i dopisuje go do miejsca zapisanego o {@code savedAt}.
     * @param updateNotification czy odświeżyć powiadomienie „Zapisano miejsce parkowania”
     */
    static void lookupAsync(Context context, ParkingStore.Spot spot, boolean updateNotification) {
        Context c = context.getApplicationContext();
        if (!Geocoder.isPresent()) return;
        Geocoder geocoder = new Geocoder(c, Locale.getDefault());

        if (Build.VERSION.SDK_INT >= 33) {
            geocoder.getFromLocation(spot.latitude, spot.longitude, 1, new Geocoder.GeocodeListener() {
                @Override
                public void onGeocode(List<Address> addresses) {
                    apply(c, spot, addresses, updateNotification);
                }

                @Override
                public void onError(String message) {
                    EventLog.log(c, "Adres: nie udało się ustalić (" + message + ")");
                }
            });
        } else {
            new Thread(() -> {
                try {
                    @SuppressWarnings("deprecation")
                    List<Address> addresses = geocoder.getFromLocation(spot.latitude, spot.longitude, 1);
                    apply(c, spot, addresses, updateNotification);
                } catch (IOException | IllegalArgumentException e) {
                    EventLog.log(c, "Adres: nie udało się ustalić (" + e.getMessage() + ")");
                }
            }, "address-lookup").start();
        }
    }

    private static void apply(Context c, ParkingStore.Spot spot, List<Address> addresses,
                              boolean updateNotification) {
        if (addresses == null || addresses.isEmpty()) return;
        Address a = addresses.get(0);
        String text = Formatters.formatAddress(a.getThoroughfare(), a.getSubThoroughfare(),
                a.getLocality(), a.getMaxAddressLineIndex() >= 0 ? a.getAddressLine(0) : null);
        if (text.isEmpty()) return;
        new ParkingStore(c).setAddress(spot.savedAt, text);
        EventLog.log(c, "Adres: " + text);
        if (updateNotification && isParkedNotificationShown(c)) {
            Notifications.showParked(c, c.getString(R.string.notif_parked_text_address, text), true);
        }
    }

    /** Odświeżamy powiadomienie tylko, jeśli użytkownik go jeszcze nie zamknął. */
    private static boolean isParkedNotificationShown(Context c) {
        NotificationManager nm = c.getSystemService(NotificationManager.class);
        if (nm == null) return false;
        for (StatusBarNotification n : nm.getActiveNotifications()) {
            if (n.getId() == Notifications.ID_PARKED) return true;
        }
        return false;
    }
}
