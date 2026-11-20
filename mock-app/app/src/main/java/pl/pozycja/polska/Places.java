package pl.pozycja.polska;

/**
 * Gotowe miejsca w Polsce (centra miast). Współrzędne w stopniach WGS84, jak w GPS.
 * Pierwsza pozycja jest domyślna.
 */
public final class Places {

    private Places() {}

    public static final class Place {
        public final String name;
        public final double lat;
        public final double lon;

        Place(String name, double lat, double lon) {
            this.name = name;
            this.lat = lat;
            this.lon = lon;
        }
    }

    public static final Place[] ALL = {
            new Place("Warszawa", 52.2297, 21.0122),
            new Place("Kraków", 50.0614, 19.9366),
            new Place("Gdańsk", 54.3520, 18.6466),
            new Place("Wrocław", 51.1079, 17.0385),
            new Place("Poznań", 52.4064, 16.9252),
            new Place("Łódź", 51.7592, 19.4560),
            new Place("Katowice", 50.2649, 19.0238),
            new Place("Szczecin", 53.4285, 14.5528),
            new Place("Lublin", 51.2465, 22.5684),
            new Place("Białystok", 53.1325, 23.1688),
            new Place("Rzeszów", 50.0412, 21.9991),
            new Place("Zakopane", 49.2992, 19.9496),
    };

    /** Domyślne miejsce: Warszawa. */
    public static Place defaultPlace() {
        return ALL[0];
    }

    /** Miejsce o podanej nazwie albo {@code null}. */
    public static Place byName(String name) {
        if (name == null) return null;
        for (Place p : ALL) {
            if (p.name.equals(name)) return p;
        }
        return null;
    }
}
