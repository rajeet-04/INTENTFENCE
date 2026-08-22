public class DataLabel {

    public enum Sensitivity {
        PUBLIC,
        INTERNAL,
        CONFIDENTIAL,
        SECRET
    }

    public enum Provenance {
        USER,
        HOTEL_API,
        DATABASE,
        ENVIRONMENT,
        AGENT
    }

    public enum Purpose {
        DISPLAY,
        COMPARISON,
        AUTHENTICATION,
        PAYMENT,
        STORAGE
    }

    private final String dataType;
    private final Sensitivity sensitivity;
    private final Provenance provenance;
    private final Purpose purpose;

    public DataLabel(
            String dataType,
            Sensitivity sensitivity,
            Provenance provenance,
            Purpose purpose) {

        this.dataType = dataType;
        this.sensitivity = sensitivity;
        this.provenance = provenance;
        this.purpose = purpose;
    }

    public String getDataType() {
        return dataType;
    }

    public Sensitivity getSensitivity() {
        return sensitivity;
    }

    public Provenance getProvenance() {
        return provenance;
    }

    public Purpose getPurpose() {
        return purpose;
    }
}