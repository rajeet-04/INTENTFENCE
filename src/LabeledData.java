public class LabeledData {

    private final String value;
    private final DataLabel label;

    public LabeledData(String value, DataLabel label) {
        this.value = value;
        this.label = label;
    }

    public String getValue() {
        return value;
    }

    public DataLabel getLabel() {
        return label;
    }
}