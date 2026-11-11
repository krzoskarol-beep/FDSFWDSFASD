package pl.gps.pozycja;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;

import com.google.android.gms.common.ConnectionResult;
import com.google.android.gms.common.GoogleApiAvailability;
import com.google.android.gms.location.ActivityRecognition;
import com.google.android.gms.location.ActivityTransition;
import com.google.android.gms.location.ActivityTransitionRequest;
import com.google.android.gms.location.DetectedActivity;

import java.util.Arrays;
import java.util.function.Consumer;

/**
 * Automatyczne zapisywanie parkowania: aplikacja sama rozpoznaje jazdę samochodem dzięki
 * rozpoznawaniu aktywności z usług Google Play (zdarzenia „w pojeździe” / „poza pojazdem”).
 * Rozpoznawanie działa w tle bez GPS, więc prawie nie zużywa baterii; GPS włącza się
 * dopiero w trakcie jazdy ({@link DrivingService}).
 */
final class AutoParking {

    static final String ACTION_TRANSITION = "pl.gps.pozycja.ACTIVITY_TRANSITION";

    private static final String PREFS = "auto_parking";
    private static final String K_ENABLED = "enabled";
    /** Ostatnie zdarzenie z Google: true po „w pojeździe”, false po „poza pojazdem”. */
    private static final String K_IN_VEHICLE = "inVehicle";

    private AutoParking() { }

    private static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static boolean isEnabled(Context c) {
        return prefs(c).getBoolean(K_ENABLED, false);
    }

    static boolean isPlayServicesAvailable(Context c) {
        return GoogleApiAvailability.getInstance().isGooglePlayServicesAvailable(c)
                == ConnectionResult.SUCCESS;
    }

    // ------------------------------------------------------------------ stan „w pojeździe”

    static void setInVehicle(Context c, boolean inVehicle) {
        prefs(c).edit().putBoolean(K_IN_VEHICLE, inVehicle).apply();
    }

    static boolean isInVehicle(Context c) {
        return prefs(c).getBoolean(K_IN_VEHICLE, false);
    }

    /** Po restarcie telefonu stan jest nieznany; Google zgłosi go od nowa. */
    static void clearInVehicle(Context c) {
        prefs(c).edit().remove(K_IN_VEHICLE).apply();
    }

    // ------------------------------------------------------------------ uprawnienia

    private static boolean granted(Context c, String permission) {
        return c.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED;
    }

    static boolean hasActivityRecognitionPermission(Context c) {
        return Build.VERSION.SDK_INT < 29 || granted(c, Manifest.permission.ACTIVITY_RECOGNITION);
    }

    static boolean hasBackgroundLocationPermission(Context c) {
        return Build.VERSION.SDK_INT < 29 || granted(c, Manifest.permission.ACCESS_BACKGROUND_LOCATION);
    }

    /** Wszystko, bez czego zapis w tle nie zadziała (powiadomienia są opcjonalne). */
    static boolean hasRequiredPermissions(Context c) {
        return granted(c, Manifest.permission.ACCESS_FINE_LOCATION)
                && hasBackgroundLocationPermission(c)
                && hasActivityRecognitionPermission(c);
    }

    // ------------------------------------------------------------------ rejestracja w Google

    private static PendingIntent transitionsIntent(Context c) {
        Intent i = new Intent(c, TransitionReceiver.class).setAction(ACTION_TRANSITION);
        // Usługi Google dopisują do tego Intentu wynik, więc musi być modyfikowalny.
        int flags = PendingIntent.FLAG_UPDATE_CURRENT
                | (Build.VERSION.SDK_INT >= 31 ? PendingIntent.FLAG_MUTABLE : 0);
        return PendingIntent.getBroadcast(c, 0, i, flags);
    }

    /** Włącza rozpoznawanie jazdy. Uprawnienia muszą już być przyznane. */
    @SuppressLint("MissingPermission") // sprawdzane przez hasRequiredPermissions()
    static void enable(Context context, Runnable onSuccess, Consumer<Exception> onFailure) {
        Context c = context.getApplicationContext();
        if (!hasRequiredPermissions(c)) {
            EventLog.log(c, "Nie można włączyć: brak uprawnień");
            if (onFailure != null) onFailure.accept(new SecurityException("missing permissions"));
            return;
        }
        ActivityTransitionRequest request = new ActivityTransitionRequest(Arrays.asList(
                new ActivityTransition.Builder()
                        .setActivityType(DetectedActivity.IN_VEHICLE)
                        .setActivityTransition(ActivityTransition.ACTIVITY_TRANSITION_ENTER)
                        .build(),
                new ActivityTransition.Builder()
                        .setActivityType(DetectedActivity.IN_VEHICLE)
                        .setActivityTransition(ActivityTransition.ACTIVITY_TRANSITION_EXIT)
                        .build()));
        try {
            ActivityRecognition.getClient(c)
                    .requestActivityTransitionUpdates(request, transitionsIntent(c))
                    .addOnSuccessListener(v -> {
                        prefs(c).edit().putBoolean(K_ENABLED, true).apply();
                        EventLog.log(c, "Rozpoznawanie jazdy włączone (usługi Google)");
                        if (onSuccess != null) onSuccess.run();
                    })
                    .addOnFailureListener(e -> {
                        EventLog.log(c, "BŁĄD rejestracji rozpoznawania jazdy: " + e);
                        if (onFailure != null) onFailure.accept(e);
                    });
        } catch (SecurityException e) {
            EventLog.log(c, "BŁĄD rejestracji rozpoznawania jazdy: " + e);
            if (onFailure != null) onFailure.accept(e);
        }
    }

    /**
     * Usługi Google zapominają rejestrację po restarcie telefonu i aktualizacji aplikacji,
     * więc odnawiamy ją wtedy (i przy każdym otwarciu aplikacji, co nic nie kosztuje).
     */
    static void reRegisterIfEnabled(Context c) {
        if (!isEnabled(c)) return;
        if (!hasRequiredPermissions(c)) {
            EventLog.log(c, "UWAGA: automatyczne zapisywanie włączone, ale brakuje uprawnień");
        } else if (!isPlayServicesAvailable(c)) {
            EventLog.log(c, "UWAGA: usługi Google Play niedostępne");
        } else {
            enable(c, null, e -> { });
        }
    }

    @SuppressLint("MissingPermission")
    static void disable(Context context) {
        Context c = context.getApplicationContext();
        prefs(c).edit().putBoolean(K_ENABLED, false).remove(K_IN_VEHICLE).apply();
        EventLog.log(c, "Automatyczne zapisywanie wyłączone");
        if (isPlayServicesAvailable(c)) {
            try {
                ActivityRecognition.getClient(c).removeActivityTransitionUpdates(transitionsIntent(c));
            } catch (SecurityException e) {
                // uprawnienie już odebrane: system i tak nie wysyła zdarzeń
            }
        }
        DrivingService.cancel(c);
    }
}
