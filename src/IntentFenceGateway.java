public class IntentFenceGateway {

    public static void sendMessage(LabeledData data) {

        DataLabel label = data.getLabel();

        boolean allowed =
                PolicyEngine.isAllowed(
                        label,
                        "SEND_MESSAGE"
                );

        System.out.println(
                "Data Type: " + label.getDataType()
        );

        System.out.println(
                "Sensitivity: " + label.getSensitivity()
        );

        System.out.println(
                "Provenance: " + label.getProvenance()
        );

        System.out.println(
                "Purpose: " + label.getPurpose()
        );

        if (allowed) {

            System.out.println("DECISION: ALLOW");
            System.out.println(
                    "Message: " + data.getValue()
            );

        } else {

            System.out.println("DECISION: BLOCK");
            System.out.println(
                    "Reason: Sensitive data cannot be sent"
            );
        }
    }
}