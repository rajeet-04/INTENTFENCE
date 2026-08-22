public class Phase4Test {

    public static void main(String[] args) {

        // -----------------------------
        // TEST 1: HOTEL PRICE
        // -----------------------------

        DataLabel hotelLabel =
                new DataLabel(
                        "HOTEL_PRICE",
                        DataLabel.Sensitivity.PUBLIC,
                        DataLabel.Provenance.HOTEL_API,
                        DataLabel.Purpose.DISPLAY
                );

        LabeledData hotelPrice =
                new LabeledData(
                        "Hotel price: ₹4500",
                        hotelLabel
                );

        System.out.println("========== TEST 1 ==========");
        System.out.println("Sending hotel price...");
        
        IntentFenceGateway.sendMessage(hotelPrice);


        // -----------------------------
        // TEST 2: API KEY
        // -----------------------------

        DataLabel apiKeyLabel =
                new DataLabel(
                        "API_KEY",
                        DataLabel.Sensitivity.SECRET,
                        DataLabel.Provenance.ENVIRONMENT,
                        DataLabel.Purpose.AUTHENTICATION
                );

        LabeledData apiKey =
                new LabeledData(
                        "sk_live_123456",
                        apiKeyLabel
                );

        System.out.println();
        System.out.println("========== TEST 2 ==========");
        System.out.println("Sending API key...");

        IntentFenceGateway.sendMessage(apiKey);
    }
}