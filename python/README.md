# Plato SDK


## Usage
**Install the plato-sdk library**
```bash
pip install plato-sdk
```

**Set Plato api key enviornment variable**
```bash
PLATO_API_KEY=
```


**Create an enviornment and connect to it using the cdp_url**
```python
import asyncio
import os
from plato import Plato, PlatoTask
from plato.examples.doordash_tasks import all_tasks as doordash_tasks

base_prompt = """
You are a helpful assistant that can help me buy food from doordash.
start by going to {start_url}. Do not navigate to other websites.
While you can't finish the checkout process becuase you need user permission,
you can add items to cart and see the total price. Do not end the task until you have added the necessary items to cart.
Here is the task:
{prompt}

Make sure to complete the checkout process once you've added the necessary items to cart.
The task is not complete until the order is sent and paid for.
You do not need my permission to and place an order.
"""

async def run_task(client: Plato, task: PlatoTask):
    env = await client.make_environment(task.env_id, open_page_on_start=False)

    await env.wait_for_ready()
    await env.reset(task)

    cdp_url = await env.get_cdp_url()

    prompt = base_prompt.format(start_url=task.start_url, prompt=task.prompt)

    # live view url to watch live
    live_view_url = await env.get_live_view_url()
    print(f"Live view URL: {live_view_url}")


    try:
        # connect agent and run
        await YourAgent.run(cdp_url, prompt)

        result = await env.evaluate()
        print(f"Evaluation result: {result}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await env.close()


async def main():
    client = Plato(api_key=os.environ.get("PLATO_API_KEY"))
    for task in doordash_tasks:
        await run_task(client, task)


if __name__ == "__main__":
    asyncio.run(main())

```


## State mutations
**State mutations returns the diffs of all modified fields**

```python
# add item to cart
...

state_mutations: dict = env.get_state()
```
This returns a JSON object like this:
```json
{
    "success": true,
    "state": {
        "added": {},
        "removed": {},
        "modified": {
            "detailed_carts": {
                "old": [],
                "new": [
                    {
                        "id": "5b227ce7-d0e9-47af-93c4-d8acfc5134d3",
                        "hasError": null,
                        "isConsumerPickup": false,
                        "isConvenienceCart": false,
                        "isPrescriptionDelivery": false,
                        "prescriptionStoreInfo": null,
                        "isMerchantShipping": false,
                        "offersDelivery": true,
                        "offersPickup": true,
                        "subtotal": 1499,
                        "urlCode": null,
                        "groupCart": false,
                        "groupCartType": null,
                        "groupCartPollInterval": null,
                        "isCatering": false,
                        "isSameStoreCatering": null,
                        "isBundle": false,
                        "bundleType": null,
                        "fulfillmentType": null,
                        "originalBundleOrderCartId": null,
                        "cartStatusType": null,
                        "cateringInfo": null,
                        "shortenedUrl": null,
                        "maxIndividualCost": null,
                        "serviceRateMessage": null,
                        "isOutsideDeliveryRegion": null,
                        "currencyCode": null,
                        "asapMinutesRange": null,
                        "orderTimeAvailability": null,
                        "menu": {
                            "id": "20016546",
                            "hoursToOrderInAdvance": null,
                            "name": null,
                            "minOrderSize": null,
                            "isCatering": false,
                            "typename": "Menu"
                        },
                        "creator": {
                            "id": "56349731",
                            "firstName": "Rob",
                            "lastName": "Farlow",
                            "localizedNames": {
                                "informalName": "Rob",
                                "formalName": "Rob Farlow",
                                "formalNameAbbreviated": "Rob F",
                                "typename": "LocalizedNames"
                            },
                            "typename": "OrderCartCreator"
                        },
                        "deliveries": null,
                        "submittedAt": null,
                        "restaurant": {
                            "id": "24770143",
                            "name": "Popstar shawarma",
                            "maxOrderSize": 0,
                            "coverImgUrl": "https://img.cdn4dd.com/cdn-cgi/image/fit=contain,width=1200,height=672,format=auto/https://doordash-static.s3.amazonaws.com/media/restaurant/cover/12699cb8-d1bf-469e-8c5b-4da529838942.jpg",
                            "businessHeaderImgUrl": "https://img.cdn4dd.com/cdn-cgi/image/fit=contain,width=1200,height=672,format=auto/https://doordash-static.s3.amazonaws.com/media/store/header/3eed46fc-3637-47fa-9378-e5848e125798.jpg",
                            "coverSquareImgUrl": "https://img.cdn4dd.com/cdn-cgi/image/fit=contain,width=1200,height=672,format=auto/https://doordash-static.s3.amazonaws.com/media/restaurant/cover_square/f8e23996-e307-42b7-859e-3e96b954d8a7.PNG",
                            "squareCoverImgUrl": null,
                            "slug": null,
                            "address": {
                                "printableAddress": null,
                                "street": "91 6th Street",
                                "lat": 37.781284,
                                "lng": -122.40871,
                                "city": "San Francisco",
                                "state": "CA",
                                "postalCode": null,
                                "country": null,
                                "displayAddress": "91 6th St, San Francisco, CA 94103, USA",
                                "typename": "Address"
                            },
                            "business": {
                                "id": "11490330",
                                "name": "Popstar shawarma",
                                "typename": "Business"
                            },
                            "orderProtocol": null,
                            "idealGroupSize": null,
                            "highQualitySubtotalThreshold": null,
                            "shouldShowStoreLogo": null,
                            "isConsumerSubscriptionEligible": null,
                            "bulkSubstitutionPreference": null,
                            "merchantPromotions": null,
                            "requiresCheckIn": null,
                            "offersPackageReturns": false,
                            "snapMerchantId": null,
                            "typename": "Restaurant"
                        },
                        "storeDisclaimers": [],
                        "orders": [
                            {
                                "id": "62df4926-0c9e-4111-a60e-9cb0ccf8b69f",
                                "consumer": {
                                    "id": "56349731",
                                    "firstName": "Rob",
                                    "lastName": "Farlow",
                                    "localizedNames": {
                                        "informalName": "Rob",
                                        "formalName": "Rob Farlow",
                                        "formalNameAbbreviated": "Rob F",
                                        "typename": "LocalizedNames"
                                    },
                                    "typename": "OrderConsumer"
                                },
                                "isSubCartFinalized": false,
                                "orderItems": [
                                    {
                                        "id": "395040ed-40fc-47d7-9076-77141afd26a8",
                                        "options": [],
                                        "cartItemStatusType": "CART_ITEM_STATUS_TYPE_UNSPECIFIED",
                                        "nestedOptions": "[]",
                                        "specialInstructions": "",
                                        "substitutionPreference": "substitute",
                                        "quantity": 1,
                                        "singlePrice": null,
                                        "priceOfTotalQuantity": 1499,
                                        "priceDisplayString": "$14.99",
                                        "nonDiscountPriceDisplayString": null,
                                        "continuousQuantity": null,
                                        "unit": "ea",
                                        "purchaseType": "PURCHASE_TYPE_UNIT",
                                        "estimatedPricingDescription": "",
                                        "increment": null,
                                        "discounts": null,
                                        "item": {
                                            "id": "7559717819",
                                            "imageUrl": "https://img.cdn4dd.com/cdn-cgi/image/fit=contain,width=1200,height=672,format=auto/https://doordash-static.s3.amazonaws.com/media/photosV2/895bfa37-0194-46f5-97ad-88edc728e5e8-retina-large.jpg",
                                            "name": "1. Chicken Sarookh Wrap",
                                            "price": 1499,
                                            "minAgeRequirement": 0,
                                            "restrictionInfo": null,
                                            "category": {
                                                "title": "",
                                                "typename": "OrderCartItemCategory"
                                            },
                                            "extras": null,
                                            "itemTagsList": [],
                                            "typename": "OrderCartItem"
                                        },
                                        "bundleStore": null,
                                        "giftInfo": null,
                                        "badges": null,
                                        "nudgeList": null,
                                        "promoNudgeList": null,
                                        "restrictionInfo": null,
                                        "isRoutineReorderEligible": false,
                                        "itemLevelDiscountMonetaryFields": {
                                            "currency": null,
                                            "displayString": null,
                                            "decimalPlaces": null,
                                            "unitAmount": null,
                                            "__typename": "AmountMonetaryFields"
                                        },
                                        "typename": "OrderItem"
                                    }
                                ],
                                "paymentCard": null,
                                "paymentLineItems": null,
                                "isOrderRoutineReorderEligible": false,
                                "typename": "Order"
                            }
                        ],
                        "selectedDeliveryOption": null,
                        "teamAccount": null,
                        "total": 1918,
                        "totalBeforeDiscountsAndCredits": 1499,
                        "footerDetails": null,
                        "orderQualityInfo": null,
                        "discountBannerDetails": [],
                        "shouldApplyCredits": true,
                        "invalidItems": null,
                        "domain": null,
                        "containsAlcohol": false,
                        "foodAlcoholConstraintCartLevel": null,
                        "commissionMessage": null,
                        "scheduledDeliveryAvailable": false,
                        "enableNewScheduleAheadUi": false,
                        "deliveryOptionsUiConfig": null,
                        "preselectedOptionUpdate": null,
                        "isDigitalWalletAllowed": false,
                        "isPreTippable": true,
                        "hideSalesTax": false,
                        "paymentProtocol": null,
                        "merchantShippingDayRangeString": null,
                        "merchantShippingDetails": null,
                        "totalCreditsAvailable": null,
                        "creditsApplicableBeforeTip": false,
                        "creditsApplicableBeforeTipDetails": null,
                        "showAccessibilityCompliance": false,
                        "totalSavings": null,
                        "taxAmount": null,
                        "tipAmount": null,
                        "merchantTipAmount": null,
                        "tipPercentageArgument": null,
                        "dasherFee": null,
                        "overauthTotal": null,
                        "legislativeFeeDetails": [],
                        "deliveryFee": null,
                        "deliveryFeeDetails": null,
                        "appliedServiceFee": null,
                        "minOrderFee": null,
                        "minOrderSubtotal": null,
                        "adsVertical": null,
                        "asapTimeRange": null,
                        "asapPickupTimeRange": null,
                        "asapNumMinutesUntilClose": null,
                        "asapPickupNumMinutesUntilClose": null,
                        "extraSosDeliveryFee": null,
                        "fulfillsOwnDeliveries": false,
                        "asapDeliveryOverrideTitle": null,
                        "asapDeliveryAvailable": true,
                        "asapPickupAvailable": true,
                        "scheduledDeliveryOptionQuoteMessage": null,
                        "bundleDetails": null,
                        "deliveryOptions": [],
                        "minAgeRequirement": null,
                        "selfDeliveryType": null,
                        "serviceRateDetails": null,
                        "providesExternalCourierTracking": false,
                        "routineReorderTimeSlots": [],
                        "routineReorderWeekIntervals": [],
                        "supplementalPaymentEligibleAmountsList": [],
                        "supplementalAuthorizedPaymentDetailsList": [],
                        "menuOptions": [],
                        "storeOrderCarts": [],
                        "consumerPromotion": null,
                        "allConsumerPromotion": null,
                        "discountDetails": null,
                        "expenseOrderOptions": null,
                        "companyPaymentInfo": null,
                        "paymentProfileType": null,
                        "creditsBackDetails": null,
                        "isDashpassApplied": false,
                        "pricingQuoteId": null,
                        "ageRestrictedIdVerificationInfo": null,
                        "signatureRequired": false,
                        "messagesAndBanners": null,
                        "appliedMxLoyaltyRewards": null,
                        "lineItemTooltipData": [],
                        "eligibleSubscription": null,
                        "recurringDeliveryDetails": null,
                        "loyaltyPointsSummary": null,
                        "differentialPricingDetails": null,
                        "applicableMxLoyaltyRewards": null,
                        "applicableExternalGiftCardDetails": null,
                        "asapDeliveryOverrideSubtitle": null,
                        "typename": "OrderCart"
                    }
                ]
            }
        }
    }
}
```




