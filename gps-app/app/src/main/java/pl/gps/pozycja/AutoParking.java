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
 * Automatyczne zapisywanie parkowania: rejestruje w usługach Google powiadomienia
 * o rozpoczęciu i zakończeniu jazdy samochodem. Rozpoznawanie aktywności działa
 * w tle cały czas, prawie bez zużycia baterii (bez GPS).
 */
final class AutoParking {

    static final String ACTION_TRANSITION = "pl.gps.pozycja.ACTIVITY_TRANSITION";

    private static final String PREFS = "auto_parking";
    private static final String K_ENABLED = "enabled";

    private AutoParking() { }

    static boolean isPlayServicesAvailable(Context c) {
        return GoogleApiAvailability.getInstance().isGooglePlayServicesAvailable(c)
                == ConnectionResult.SUCCESS;
    }

    static boolean isEnabled(Context c) {
        return prefs(c).getBoolean(K_ENABLED, false);
    }

    private static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private static boolean granted(Context c, String permission) {
        return c.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED;
    }

    static boolean hasActivityRecognitionPermission(Context c) {
        return Build.VERSION.SDK_INT < 29 || granted(c, Manifest.permission.ACTIVITY_RECOGNITION);
    }

    static boolean hasBackgroundLocationPermission(Context c) {
        return Build.VERSION.SDK_INT < 29 || granted(c, Manifest.permission.ACCESS_BACKGROUND_LOCATION);
    }

    /** Wszystko, bez czego wykrywanie w tle nie zadziała (powiadomienia są opcjonalne). */
    static boolean hasRequiredPermissions(Context c) {
        return granted(c, Manifest.permission.ACCESS_FINE_LOCATION)
                && hasActivityRecognitionPermission(c)
                && hasBackgroundLocationPermission(c);
    }

    private static PendingIntent transitionsIntent(Context c) {
        Intent i = new Intent(c, TransitionReceiver.class).setAction(ACTION_TRANSITION);
        // Usługi Google dopisują do tego Intentu wynik, więc musi być modyfikowalny.
        int flags = PendingIntent.FLAG_UPDATE_CURRENT
                | (Build.VERSION.SDK_INT >= 31 ? PendingIntent.FLAG_MUTABLE : 0);
        return PendingIntent.getBroadcast(c, 0, i, flags);
    }

    /** Włącza wykrywanie jazdy. Uprawnienia muszą już być przyznane. */
    @SuppressLint("MissingPermission") // sprawdzane przez hasRequiredPermissions()
    static void enable(Context context, Runnable onSuccess, Consumer<Exception> onFailure) {
        Context c = context.getApplicationContext();
        if (!hasRequiredPermissions(c)) {
            onFailure.accept(new SecurityException("missing permissions"));
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
                        if (onSuccess != null) onSuccess.run();
                    })
                    .addOnFailureListener(e -> {
                        if (onFailure != null) onFailure.accept(e);
                    });
        } catch (SecurityException e) {
            if (onFailure != null) onFailure.accept(e);
        }
    }

    /** Ponowna rejestracja, np. po restarcie telefonu albo aktualizacji aplikacji. */
    static void reRegisterIfEnabled(Context c) {
        if (isEnabled(c) && hasRequiredPermissions(c) && isPlayServicesAvailable(c)) {
            enable(c, null, e -> { });
        }
    }

    @SuppressLint("MissingPermission")
    static void disable(Context context) {
        Context c = context.getApplicationContext();
        prefs(c).edit().putBoolean(K_ENABLED, false).apply();
        try {
            ActivityRecognition.getClient(c).removeActivityTransitionUpdates(transitionsIntent(c));
        } catch (SecurityException e) {
            // uprawnienie już odebrane: system i tak nie wysyła zdarzeń
        }
        DrivingService.cancel(c);
    }
}
