public class PolicyEngine {

    public static boolean isAllowed(
            DataLabel label,
            String action) {

        // Secret data cannot be sent to the user
        if (label.getSensitivity()
                == DataLabel.Sensitivity.SECRET
                && action.equals("SEND_MESSAGE")) {

            return false;
        }

        // Otherwise allow
        return true;
    }
}