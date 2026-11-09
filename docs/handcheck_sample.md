# Hand-check sample (synthetic data)

40 cases, stratified by category x decision (seed 7). Built from tool outputs only.

### GEN-002 - item_not_received / strong (-)
- Dispute DSP-100014: visa 13.1 (processor cat: product_not_received), $168.00; issuer msg: "Cardholder claims package did not arrive at shipping address."; 442.0 h left
- Order ORD-100734 total $168.00, AVS Y / CVV M, ship==bill False, policy yes, listing snapshot yes
- Shipment: USPS Priority Mail, tracking SYN94481277257295, status delivered, addr match True, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 450 d old at order; prior orders 2, undisputed+delivered in 120-365d window 2, same device+IP 1; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Hi, the package arrived yesterday. Quick question - can I exchange for a different size?
- **Label**: present ['carrier_tracking', 'delivery_confirmation', 'address_match'] | missing [] | strong ['customer_ack_receipt'] | conflicts - | fault - | credit_full False | p=0.77 EV=$94.36 | triggers - | **FIGHT** (positive_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-003 - item_not_received / strong (-)
- Dispute DSP-100015: visa 13.1 (processor cat: product_not_received), $89.00; issuer msg: "CH advises order not delivered; contacted merchant without resolution."; 476.0 h left
- Order ORD-100736 total $89.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: FedEx Home Delivery, tracking SYNFX192351764123, status delivered, addr match True, sig False, photo False, dispatch photo True; last event: Delivered, left at front door
- Customer: account 375 d old at order; prior orders 1, undisputed+delivered in 120-365d window 1, same device+IP 1; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['carrier_tracking', 'delivery_confirmation', 'address_match'] | missing [] | strong [] | conflicts - | fault - | credit_full False | p=0.7 EV=$27.3 | triggers - | **FIGHT** (positive_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-004 - item_not_received / strong (-)
- Dispute DSP-100016: mastercard 4853 (processor cat: general), $112.00; issuer msg: "Cardholder claims package did not arrive at shipping address."; 801.0 h left
- Order ORD-100737 total $112.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: USPS Priority Mail, tracking SYN94842038654277, status delivered, addr match True, sig False, photo True, dispatch photo True; last event: Delivered, photo taken at front door
- Customer: account 548 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Is my order still coming? The tracking page just says in transit.
    - [agent] Thanks for reaching out. Carriers can be delayed this time of year; please allow a few more business days.
- **Label**: present ['carrier_tracking', 'delivery_confirmation', 'address_match'] | missing [] | strong ['proof_of_delivery'] | conflicts - | fault - | credit_full False | p=0.77 EV=$51.24 | triggers - | **FIGHT** (positive_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-010 - item_not_received / strong (-)
- Dispute DSP-100022: mastercard 4853 (processor cat: general), $395.00; issuer msg: "Cardholder claims package did not arrive at shipping address."; 886.0 h left
- Order ORD-100750 total $395.00, AVS Y / CVV M, ship==bill False, policy yes, listing snapshot yes
- Shipment: USPS Priority Mail, tracking SYN94242079303713, status delivered, addr match True, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 1293 d old at order; prior orders 1, undisputed+delivered in 120-365d window 1, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Got my order today, thanks. Do you have care instructions for it?
- **Label**: present ['carrier_tracking', 'delivery_confirmation', 'address_match'] | missing [] | strong ['customer_ack_receipt'] | conflicts - | fault - | credit_full False | p=0.77 EV=$269.15 | triggers - | **FIGHT** (positive_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-016 - item_not_received / weak (no_address_data)
- Dispute DSP-100028: mastercard 4853 (processor cat: general), $329.00; issuer msg: "Cardholder states merchandise was never received."; 854.0 h left
- Order ORD-100761 total $329.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: UPS Ground, tracking SYN1Z564750590714, status delivered, addr match None, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 526 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['carrier_tracking', 'delivery_confirmation'] | missing ['address_match'] | strong [] | conflicts - | fault - | credit_full False | p=0.28 EV=$57.12 | triggers ['missing_required_evidence'] | **ESCALATE** (missing_required_evidence)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-026 - item_not_received / conflicting (agent_admitted_misdelivery)
- Dispute DSP-100038: mastercard 4853 (processor cat: general), $345.00; issuer msg: "Cardholder states merchandise was never received."; 884.0 h left
- Order ORD-100780 total $345.00, AVS Y / CVV M, ship==bill False, policy yes, listing snapshot yes
- Shipment: USPS Priority Mail, tracking SYN94875128012881, status delivered, addr match True, sig True, photo False, dispatch photo False; last event: Delivered, signed by recipient
- Customer: account 375 d old at order; prior orders 2, undisputed+delivered in 120-365d window 2, same device+IP 1; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Is my order still coming? The tracking page just says in transit.
    - [agent] Thanks for reaching out. Carriers can be delayed this time of year; please allow a few more business days.
    - [customer] Do you ship to PO boxes?
    - [customer] I never got this package even though it shows delivered.
    - [agent] Apologies - the carrier confirmed a misdelivery on their side. Let me see what we can do about a replacement.
- **Label**: present ['carrier_tracking', 'delivery_confirmation', 'address_match'] | missing [] | strong ['proof_of_delivery'] | conflicts ['merchant_acknowledged_nondelivery'] | fault - | credit_full False | p=0.462 EV=$124.39 | triggers ['conflicting_evidence'] | **ESCALATE** (conflicting_evidence)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-034 - item_not_received / deadline_near (-)
- Dispute DSP-100046: mastercard 4853 (processor cat: general), $549.00; issuer msg: "Goods not received per cardholder. Expected delivery date has passed."; 31.0 h left
- Order ORD-100800 total $549.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: USPS Priority Mail, tracking SYN94157106530253, status delivered, addr match True, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 1010 d old at order; prior orders 3, undisputed+delivered in 120-365d window 3, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Got my order today, thanks. Do you have care instructions for it?
- **Label**: present ['carrier_tracking', 'delivery_confirmation', 'address_match'] | missing [] | strong ['customer_ack_receipt'] | conflicts - | fault - | credit_full False | p=0.77 EV=$387.73 | triggers ['deadline_near'] | **ESCALATE** (deadline_near)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-035 - item_not_received / deadline_passed (-)
- Dispute DSP-100047: visa 13.1 (processor cat: product_not_received), $549.00; issuer msg: ""; -16.0 h left
- Order ORD-100801 total $549.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: FedEx Home Delivery, tracking SYNFX325456169588, status delivered, addr match True, sig False, photo False, dispatch photo True; last event: Delivered, left at front door
- Customer: account 806 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Can I change the email on my account?
- **Label**: present ['carrier_tracking', 'delivery_confirmation', 'address_match'] | missing [] | strong [] | conflicts - | fault - | credit_full False | p=0.7 EV=$349.3 | triggers - | **ACCEPT** (deadline_passed)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-044 - item_not_received / repeat_disputer (-)
- Dispute DSP-100058: amex C08 (processor cat: product_not_received), $279.00; issuer msg: ""; 210.0 h left
- Order ORD-100824 total $279.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: UPS Ground, tracking SYN1Z982943400520, status delivered, addr match True, sig True, photo False, dispatch photo False; last event: Delivered, signed by recipient
- Customer: account 1386 d old at order; prior orders 5, undisputed+delivered in 120-365d window 3, same device+IP 0; other disputes 2
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['carrier_tracking', 'delivery_confirmation', 'address_match'] | missing [] | strong ['proof_of_delivery'] | conflicts - | fault - | credit_full False | p=0.77 EV=$179.83 | triggers ['repeat_disputer'] | **ESCALATE** (repeat_disputer)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-047 - item_not_received / low_amount (-)
- Dispute DSP-100064: amex C08 (processor cat: product_not_received), $16.94; issuer msg: "Cardholder states merchandise was never received."; 231.0 h left
- Order ORD-100838 total $16.94, AVS Y / CVV M, ship==bill False, policy yes, listing snapshot yes
- Shipment: FedEx Home Delivery, tracking SYNFX214207742691, status delivered, addr match True, sig True, photo False, dispatch photo False; last event: Delivered, signed by recipient
- Customer: account 822 d old at order; prior orders 3, undisputed+delivered in 120-365d window 3, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['carrier_tracking', 'delivery_confirmation', 'address_match'] | missing [] | strong ['proof_of_delivery'] | conflicts - | fault - | credit_full False | p=0.77 EV=$-21.96 | triggers - | **ACCEPT** (negative_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-048 - item_not_received / merchant_fault (lost)
- Dispute DSP-100065: mastercard 4853 (processor cat: general), $129.00; issuer msg: "CH advises order not delivered; contacted merchant without resolution."; 846.0 h left
- Order ORD-100841 total $129.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: UPS Ground, tracking SYN1Z917030637459, status lost, addr match None, sig False, photo False, dispatch photo True; last event: Package could not be located. Claim opened by carrier.
- Customer: account 375 d old at order; prior orders 2, undisputed+delivered in 120-365d window 2, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Hi, my tracking hasn't updated in a few days. Can you check where my order is?
    - [agent] Thanks for reaching out. Carriers can be delayed this time of year; please allow a few more business days.
- **Label**: present ['carrier_tracking'] | missing ['delivery_confirmation', 'address_match'] | strong [] | conflicts - | fault ['shipment_lost'] | credit_full False | p=0.112 EV=$-20.55 | triggers ['missing_required_evidence'] | **ACCEPT** (merchant_at_fault)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-049 - item_not_received / merchant_fault (returned_to_sender)
- Dispute DSP-100066: mastercard 4853 (processor cat: general), $189.00; issuer msg: "Goods not received per cardholder. Expected delivery date has passed."; 791.0 h left
- Order ORD-100842 total $189.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: USPS Priority Mail, tracking SYN94074993243556, status returned_to_sender, addr match None, sig False, photo False, dispatch photo True; last event: Returned to sender
- Customer: account 1214 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Hi, my tracking hasn't updated in a few days. Can you check where my order is?
    - [agent] Sorry for the wait! I've asked the carrier for an update and will follow up.
- **Label**: present ['carrier_tracking'] | missing ['delivery_confirmation', 'address_match'] | strong [] | conflicts - | fault ['shipment_returned_to_sender'] | credit_full False | p=0.112 EV=$-13.83 | triggers ['missing_required_evidence'] | **ACCEPT** (merchant_at_fault)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-051 - fraud / strong (-)
- Dispute DSP-100068: visa 10.4 (processor cat: fraudulent), $145.00; issuer msg: "Cardholder does not recognize this transaction."; 512.0 h left
- Order ORD-100847 total $145.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: USPS Priority Mail, tracking SYN94557912616353, status delivered, addr match True, sig False, photo False, dispatch photo True; last event: Delivered, left at front door
- Customer: account 647 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['avs_cvv_match', 'delivery_confirmation', 'delivered_to_billing_address'] | missing [] | strong ['established_account'] | conflicts - | fault - | credit_full False | p=0.57 EV=$47.65 | triggers - | **FIGHT** (positive_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-052 - fraud / strong (-)
- Dispute DSP-100069: visa 10.4 (processor cat: fraudulent), $279.00; issuer msg: ""; 524.0 h left
- Order ORD-100848 total $279.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: UPS Ground, tracking SYN1Z975435311299, status delivered, addr match True, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 1499 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Can I change the email on my account?
- **Label**: present ['avs_cvv_match', 'delivery_confirmation', 'delivered_to_billing_address'] | missing [] | strong ['established_account'] | conflicts - | fault - | credit_full False | p=0.57 EV=$124.03 | triggers - | **FIGHT** (positive_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-057 - fraud / strong (-)
- Dispute DSP-100074: mastercard 4837 (processor cat: fraudulent), $279.00; issuer msg: "Cardholder denies participating in this card-not-present transaction."; 861.0 h left
- Order ORD-100862 total $279.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: UPS Ground, tracking SYN1Z207048084590, status delivered, addr match True, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 587 d old at order; prior orders 3, undisputed+delivered in 120-365d window 3, same device+IP 2; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['avs_cvv_match', 'delivery_confirmation', 'delivered_to_billing_address'] | missing [] | strong ['prior_undisputed_orders', 'device_ip_match', 'established_account'] | conflicts - | fault - | credit_full False | p=0.71 EV=$163.09 | triggers - | **FIGHT** (positive_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-064 - fraud / weak (avs_cvv+billing)
- Dispute DSP-100081: visa 10.4 (processor cat: fraudulent), $249.00; issuer msg: ""; 492.0 h left
- Order ORD-100874 total $249.00, AVS N / CVV M, ship==bill False, policy yes, listing snapshot yes
- Shipment: FedEx Home Delivery, tracking SYNFX976062395220, status delivered, addr match True, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 38 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['delivery_confirmation'] | missing ['avs_cvv_match', 'delivered_to_billing_address'] | strong [] | conflicts - | fault - | credit_full False | p=0.08 EV=$-15.08 | triggers ['missing_required_evidence'] | **ACCEPT** (negative_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-068 - fraud / weak (avs_cvv+billing+delivery)
- Dispute DSP-100085: amex F29 (processor cat: fraudulent), $189.00; issuer msg: "Unauthorized transaction reported. Cardholder still in possession of card."; 225.0 h left
- Order ORD-100878 total $189.00, AVS N / CVV M, ship==bill False, policy yes, listing snapshot yes
- Shipment: FedEx Home Delivery, tracking SYNFX140463194038, status in_transit, addr match None, sig False, photo False, dispatch photo False; last event: Arrived at destination facility
- Customer: account 31 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present [] | missing ['avs_cvv_match', 'delivery_confirmation', 'delivered_to_billing_address'] | strong [] | conflicts - | fault - | credit_full False | p=0.032 EV=$-28.95 | triggers ['missing_required_evidence'] | **ACCEPT** (negative_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-071 - fraud / weak (avs_cvv)
- Dispute DSP-100088: visa 10.4 (processor cat: fraudulent), $229.00; issuer msg: "CH states card was used without authorization for an online purchase."; 492.0 h left
- Order ORD-100881 total $229.00, AVS N / CVV N, ship==bill True, policy yes, listing snapshot yes
- Shipment: FedEx Home Delivery, tracking SYNFX474171038370, status delivered, addr match True, sig False, photo True, dispatch photo True; last event: Delivered, photo taken at front door
- Customer: account 60 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['delivery_confirmation', 'delivered_to_billing_address'] | missing ['avs_cvv_match'] | strong [] | conflicts - | fault - | credit_full False | p=0.2 EV=$10.8 | triggers ['missing_required_evidence'] | **ESCALATE** (missing_required_evidence)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-076 - fraud / conflicting (avs_fail_but_device_history)
- Dispute DSP-100093: visa 10.4 (processor cat: fraudulent), $395.00; issuer msg: "CH states card was used without authorization for an online purchase."; 489.0 h left
- Order ORD-100895 total $395.00, AVS N / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: FedEx Home Delivery, tracking SYNFX665377594080, status delivered, addr match True, sig False, photo False, dispatch photo True; last event: Delivered, left at front door
- Customer: account 500 d old at order; prior orders 3, undisputed+delivered in 120-365d window 3, same device+IP 1; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['delivery_confirmation', 'delivered_to_billing_address'] | missing ['avs_cvv_match'] | strong ['prior_undisputed_orders', 'device_ip_match', 'established_account'] | conflicts ['avs_cvv_failed_but_customer_history_matches'] | fault - | credit_full False | p=0.246 EV=$62.17 | triggers ['conflicting_evidence', 'missing_required_evidence'] | **ESCALATE** (conflicting_evidence)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-078 - fraud / conflicting (avs_fail_but_device_history)
- Dispute DSP-100095: mastercard 4837 (processor cat: fraudulent), $549.00; issuer msg: ""; 877.0 h left
- Order ORD-100901 total $549.00, AVS N / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: UPS Ground, tracking SYN1Z712079525940, status delivered, addr match True, sig False, photo True, dispatch photo False; last event: Delivered, photo taken at front door
- Customer: account 1420 d old at order; prior orders 2, undisputed+delivered in 120-365d window 2, same device+IP 2; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Can I change the email on my account?
- **Label**: present ['delivery_confirmation', 'delivered_to_billing_address'] | missing ['avs_cvv_match'] | strong ['prior_undisputed_orders', 'device_ip_match', 'established_account'] | conflicts ['avs_cvv_failed_but_customer_history_matches'] | fault - | credit_full False | p=0.246 EV=$100.05 | triggers ['conflicting_evidence', 'missing_required_evidence'] | **ESCALATE** (conflicting_evidence)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-081 - fraud / conflicting (avs_fail_but_device_history)
- Dispute DSP-100098: amex F29 (processor cat: fraudulent), $549.00; issuer msg: "CH states card was used without authorization for an online purchase."; 248.0 h left
- Order ORD-100910 total $549.00, AVS N / CVV N, ship==bill True, policy yes, listing snapshot yes
- Shipment: USPS Priority Mail, tracking SYN94612401253959, status delivered, addr match True, sig True, photo False, dispatch photo True; last event: Delivered, signed by recipient
- Customer: account 1194 d old at order; prior orders 2, undisputed+delivered in 120-365d window 2, same device+IP 1; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Do you ship to PO boxes?
- **Label**: present ['delivery_confirmation', 'delivered_to_billing_address'] | missing ['avs_cvv_match'] | strong ['prior_undisputed_orders', 'device_ip_match', 'established_account'] | conflicts ['avs_cvv_failed_but_customer_history_matches'] | fault - | credit_full False | p=0.246 EV=$100.05 | triggers ['conflicting_evidence', 'missing_required_evidence'] | **ESCALATE** (conflicting_evidence)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-088 - fraud / partial_refund_consistent (-)
- Dispute DSP-100105: visa 10.4 (processor cat: fraudulent), $210.45; issuer msg: "Unauthorized transaction reported. Cardholder still in possession of card."; 500.0 h left
- Order ORD-100925 total $345.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: UPS Ground, tracking SYN1Z971005342569, status delivered, addr match True, sig True, photo False, dispatch photo False; last event: Delivered, signed by recipient
- Customer: account 408 d old at order; prior orders 3, undisputed+delivered in 120-365d window 3, same device+IP 3; other disputes 0
- Refunds: $134.55; returns: none
- Messages:
    - [customer] Can I change the email on my account?
- **Label**: present ['avs_cvv_match', 'delivery_confirmation', 'delivered_to_billing_address'] | missing [] | strong ['prior_undisputed_orders', 'device_ip_match', 'established_account'] | conflicts - | fault - | credit_full False | p=0.71 EV=$114.42 | triggers - | **FIGHT** (positive_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-097 - fraud / low_amount (-)
- Dispute DSP-100121: visa 10.4 (processor cat: fraudulent), $28.95; issuer msg: ""; 423.0 h left
- Order ORD-100950 total $28.95, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: USPS Priority Mail, tracking SYN94110869450233, status delivered, addr match True, sig False, photo False, dispatch photo True; last event: Delivered, left at front door
- Customer: account 387 d old at order; prior orders 2, undisputed+delivered in 120-365d window 2, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Do you ship to PO boxes?
- **Label**: present ['avs_cvv_match', 'delivery_confirmation', 'delivered_to_billing_address'] | missing [] | strong ['prior_undisputed_orders', 'established_account'] | conflicts - | fault - | credit_full False | p=0.64 EV=$-16.47 | triggers - | **ACCEPT** (negative_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-098 - fraud / low_amount (-)
- Dispute DSP-100122: visa 10.4 (processor cat: fraudulent), $28.95; issuer msg: ""; 519.0 h left
- Order ORD-100951 total $28.95, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: FedEx Home Delivery, tracking SYNFX144168925521, status delivered, addr match True, sig False, photo True, dispatch photo False; last event: Delivered, photo taken at front door
- Customer: account 344 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['avs_cvv_match', 'delivery_confirmation', 'delivered_to_billing_address'] | missing [] | strong ['established_account'] | conflicts - | fault - | credit_full False | p=0.57 EV=$-18.5 | triggers - | **ACCEPT** (negative_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-099 - not_as_described / strong (-)
- Dispute DSP-100123: visa 13.3 (processor cat: product_unacceptable), $189.00; issuer msg: ""; 512.0 h left
- Order ORD-100953 total $189.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: USPS Priority Mail, tracking SYN94896024124232, status delivered, addr match True, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 526 d old at order; prior orders 1, undisputed+delivered in 120-365d window 1, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Can I change the email on my account?
    - [customer] This arrived with a broken part and doesn't work properly.
    - [agent] Thanks for letting us know. Please send it back with the attached return label and we'll refund you as soon as it arrives.
- **Label**: present ['product_listing', 'return_policy_accepted', 'merchant_offered_remedy'] | missing [] | strong ['no_return_attempted'] | conflicts - | fault - | credit_full False | p=0.52 EV=$63.28 | triggers - | **FIGHT** (positive_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-109 - not_as_described / strong (-)
- Dispute DSP-100133: visa 13.3 (processor cat: product_unacceptable), $279.00; issuer msg: "Cardholder says product differs materially from listing (color/size)."; 437.0 h left
- Order ORD-100974 total $279.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: UPS Ground, tracking SYN1Z659580729843, status delivered, addr match True, sig False, photo True, dispatch photo False; last event: Delivered, photo taken at front door
- Customer: account 755 d old at order; prior orders 1, undisputed+delivered in 120-365d window 1, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] This arrived with a broken part and doesn't work properly.
    - [agent] Thanks for letting us know. Please send it back with the attached return label and we'll refund you as soon as it arrives.
- **Label**: present ['product_listing', 'return_policy_accepted', 'merchant_offered_remedy'] | missing [] | strong ['no_return_attempted'] | conflicts - | fault - | credit_full False | p=0.52 EV=$110.08 | triggers - | **FIGHT** (positive_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-110 - not_as_described / strong (-)
- Dispute DSP-100134: visa 13.3 (processor cat: product_unacceptable), $229.00; issuer msg: ""; 416.0 h left
- Order ORD-100978 total $229.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: FedEx Home Delivery, tracking SYNFX799564318351, status delivered, addr match True, sig False, photo False, dispatch photo True; last event: Delivered, left at front door
- Customer: account 1238 d old at order; prior orders 3, undisputed+delivered in 120-365d window 3, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] This arrived with a broken part and doesn't work properly.
    - [agent] Sorry to hear that! I can send a replacement right away, or you can return it for a refund - just reply and let me know which you'd prefer.
- **Label**: present ['product_listing', 'return_policy_accepted', 'merchant_offered_remedy'] | missing [] | strong ['no_return_attempted', 'dispatch_photo'] | conflicts - | fault - | credit_full False | p=0.59 EV=$100.11 | triggers - | **FIGHT** (positive_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-112 - not_as_described / weak (listing)
- Dispute DSP-100136: visa 13.3 (processor cat: product_unacceptable), $155.00; issuer msg: "Cardholder says product differs materially from listing (color/size)."; 468.0 h left
- Order ORD-100984 total $155.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot NO
- Shipment: FedEx Home Delivery, tracking SYNFX084925032059, status delivered, addr match True, sig False, photo True, dispatch photo False; last event: Delivered, photo taken at front door
- Customer: account 961 d old at order; prior orders 2, undisputed+delivered in 120-365d window 2, same device+IP 1; other disputes 0
- Refunds: $0.00; returns: ['label_sent']
- Messages:
    - [customer] Material feels cheap and it's not what was described.
    - [agent] Thanks for letting us know. Please send it back with the attached return label and we'll refund you as soon as it arrives.
- **Label**: present ['return_policy_accepted', 'merchant_offered_remedy'] | missing ['product_listing'] | strong [] | conflicts - | fault - | credit_full False | p=0.18 EV=$-7.1 | triggers ['missing_required_evidence'] | **ACCEPT** (negative_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-115 - not_as_described / weak (listing+policy+remedy)
- Dispute DSP-100139: mastercard 4853 (processor cat: general), $549.00; issuer msg: "Item received is defective per cardholder."; 856.0 h left
- Order ORD-100994 total $549.00, AVS Y / CVV M, ship==bill True, policy NO, listing snapshot NO
- Shipment: USPS Priority Mail, tracking SYN94867486890364, status delivered, addr match True, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 383 d old at order; prior orders 2, undisputed+delivered in 120-365d window 2, same device+IP 2; other disputes 0
- Refunds: $0.00; returns: ['label_sent']
- Messages:
    - [customer] Material feels cheap and it's not what was described.
- **Label**: present [] | missing ['product_listing', 'return_policy_accepted', 'merchant_offered_remedy'] | strong [] | conflicts - | fault - | credit_full False | p=0.0288 EV=$-19.19 | triggers ['missing_required_evidence'] | **ACCEPT** (negative_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-116 - not_as_described / weak (listing)
- Dispute DSP-100140: visa 13.3 (processor cat: product_unacceptable), $145.00; issuer msg: "Item received is defective per cardholder."; 513.0 h left
- Order ORD-100997 total $145.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot NO
- Shipment: USPS Priority Mail, tracking SYN94450349081636, status delivered, addr match True, sig False, photo True, dispatch photo True; last event: Delivered, photo taken at front door
- Customer: account 1024 d old at order; prior orders 2, undisputed+delivered in 120-365d window 2, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: ['label_sent']
- Messages:
    - [customer] The item I received doesn't look like the photos at all. The color is completely different.
    - [agent] We're sorry it isn't what you expected. You can return it within 30 days for a full refund using the prepaid label below, or we can send a replacement.
- **Label**: present ['return_policy_accepted', 'merchant_offered_remedy'] | missing ['product_listing'] | strong ['dispatch_photo'] | conflicts - | fault - | credit_full False | p=0.25 EV=$1.25 | triggers ['missing_required_evidence'] | **ESCALATE** (missing_required_evidence)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-117 - not_as_described / weak (listing+policy)
- Dispute DSP-100141: visa 13.3 (processor cat: product_unacceptable), $345.00; issuer msg: ""; 462.0 h left
- Order ORD-101001 total $345.00, AVS Y / CVV M, ship==bill True, policy NO, listing snapshot NO
- Shipment: FedEx Home Delivery, tracking SYNFX932215064009, status delivered, addr match True, sig True, photo False, dispatch photo False; last event: Delivered, signed by recipient
- Customer: account 375 d old at order; prior orders 3, undisputed+delivered in 120-365d window 3, same device+IP 2; other disputes 0
- Refunds: $0.00; returns: ['label_sent']
- Messages:
    - [customer] The size is nothing like what the listing said. Very disappointed.
    - [agent] Thanks for letting us know. Please send it back with the attached return label and we'll refund you as soon as it arrives.
- **Label**: present ['merchant_offered_remedy'] | missing ['product_listing', 'return_policy_accepted'] | strong [] | conflicts - | fault - | credit_full False | p=0.072 EV=$-10.16 | triggers ['missing_required_evidence'] | **ACCEPT** (negative_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-124 - not_as_described / conflicting (agent_admitted_defect)
- Dispute DSP-100148: mastercard 4853 (processor cat: general), $549.00; issuer msg: "CH reports merchandise arrived damaged and merchant refused to help."; 854.0 h left
- Order ORD-101016 total $549.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: FedEx Home Delivery, tracking SYNFX178528767854, status delivered, addr match True, sig True, photo False, dispatch photo True; last event: Delivered, signed by recipient
- Customer: account 1218 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: ['label_sent']
- Messages:
    - [customer] The size is nothing like what the listing said. Very disappointed.
    - [agent] I've confirmed with our warehouse that the units from this shipment were mislabeled and do not match the listing. Apologies.
    - [agent] Thanks for letting us know. Please send it back with the attached return label and we'll refund you as soon as it arrives.
- **Label**: present ['product_listing', 'return_policy_accepted', 'merchant_offered_remedy'] | missing [] | strong ['dispatch_photo'] | conflicts ['merchant_admitted_defect'] | fault - | credit_full False | p=0.312 EV=$136.29 | triggers ['conflicting_evidence'] | **ESCALATE** (conflicting_evidence)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-125 - not_as_described / conflicting (agent_admitted_defect)
- Dispute DSP-100149: amex C32 (processor cat: product_unacceptable), $345.00; issuer msg: ""; 205.0 h left
- Order ORD-101017 total $345.00, AVS Y / CVV M, ship==bill False, policy yes, listing snapshot yes
- Shipment: UPS Ground, tracking SYN1Z882407870073, status delivered, addr match True, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 700 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] The size is nothing like what the listing said. Very disappointed.
    - [agent] You're right - this batch had a known manufacturing defect and we've pulled it from sale. We're sorry.
    - [agent] Thanks for letting us know. Please send it back with the attached return label and we'll refund you as soon as it arrives.
- **Label**: present ['product_listing', 'return_policy_accepted', 'merchant_offered_remedy'] | missing [] | strong ['no_return_attempted'] | conflicts ['merchant_admitted_defect'] | fault - | credit_full False | p=0.312 EV=$72.64 | triggers ['conflicting_evidence'] | **ESCALATE** (conflicting_evidence)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-130 - not_as_described / conflicting (agent_admitted_defect)
- Dispute DSP-100154: mastercard 4853 (processor cat: general), $395.00; issuer msg: "Cardholder says product differs materially from listing (color/size)."; 847.0 h left
- Order ORD-101031 total $395.00, AVS Y / CVV M, ship==bill False, policy yes, listing snapshot yes
- Shipment: FedEx Home Delivery, tracking SYNFX696015927221, status delivered, addr match True, sig True, photo False, dispatch photo False; last event: Delivered, signed by recipient
- Customer: account 1492 d old at order; prior orders 1, undisputed+delivered in 120-365d window 1, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
    - [customer] Do you ship to PO boxes?
    - [customer] This arrived with a broken part and doesn't work properly.
    - [agent] You're right - this batch had a known manufacturing defect and we've pulled it from sale. We're sorry.
    - [agent] Thanks for letting us know. Please send it back with the attached return label and we'll refund you as soon as it arrives.
- **Label**: present ['product_listing', 'return_policy_accepted', 'merchant_offered_remedy'] | missing [] | strong ['no_return_attempted'] | conflicts ['merchant_admitted_defect'] | fault - | credit_full False | p=0.312 EV=$88.24 | triggers ['conflicting_evidence'] | **ESCALATE** (conflicting_evidence)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-138 - not_as_described / full_refund (-)
- Dispute DSP-100162: amex C32 (processor cat: product_unacceptable), $229.00; issuer msg: ""; 248.0 h left
- Order ORD-101050 total $229.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: FedEx Home Delivery, tracking SYNFX035678817922, status delivered, addr match True, sig False, photo False, dispatch photo True; last event: Delivered, left at front door
- Customer: account 825 d old at order; prior orders 1, undisputed+delivered in 120-365d window 1, same device+IP 1; other disputes 0
- Refunds: $229.00; returns: none
- Messages:
    - [customer] Can I change the email on my account?
    - [customer] Material feels cheap and it's not what was described.
    - [agent] Thanks for letting us know. Please send it back with the attached return label and we'll refund you as soon as it arrives.
- **Label**: present ['product_listing', 'return_policy_accepted', 'merchant_offered_remedy'] | missing [] | strong ['no_return_attempted', 'dispatch_photo'] | conflicts - | fault - | credit_full True | p=0.9 EV=$171.1 | triggers - | **FIGHT** (positive_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### GEN-146 - not_as_described / merchant_fault (return_received_no_refund)
- Dispute DSP-100175: amex C32 (processor cat: product_unacceptable), $395.00; issuer msg: ""; 257.0 h left
- Order ORD-101071 total $395.00, AVS Y / CVV M, ship==bill False, policy yes, listing snapshot yes
- Shipment: USPS Priority Mail, tracking SYN94428332413112, status delivered, addr match True, sig False, photo True, dispatch photo False; last event: Delivered, photo taken at front door
- Customer: account 1270 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: ['received']
- Messages:
    - [customer] Can I change the email on my account?
    - [customer] This arrived with a broken part and doesn't work properly.
    - [agent] Thanks for letting us know. Please send it back with the attached return label and we'll refund you as soon as it arrives.
- **Label**: present ['product_listing', 'return_policy_accepted', 'merchant_offered_remedy'] | missing [] | strong [] | conflicts - | fault ['return_received_without_refund'] | credit_full False | p=0.45 EV=$142.75 | triggers - | **ACCEPT** (merchant_at_fault)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### HW-04 - fraud / hw_ce3_like_avs_fail (AVS/CVV failed but 3 prior undisputed orders from same device/IP (CE 3.0 pattern))
- Dispute DSP-100180: visa 10.4 (processor cat: fraudulent), $500.00; issuer msg: ""; 416.0 h left
- Order ORD-101081 total $500.00, AVS N / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: FedEx Home Delivery, tracking SYNFX889904227978, status delivered, addr match True, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 700 d old at order; prior orders 3, undisputed+delivered in 120-365d window 3, same device+IP 3; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['delivery_confirmation', 'delivered_to_billing_address'] | missing ['avs_cvv_match'] | strong ['prior_undisputed_orders', 'device_ip_match', 'established_account'] | conflicts ['avs_cvv_failed_but_customer_history_matches'] | fault - | credit_full False | p=0.246 EV=$88.0 | triggers ['conflicting_evidence', 'missing_required_evidence'] | **ESCALATE** (conflicting_evidence)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### HW-09 - fraud / hw_deadline_exactly_buffer (Exactly 72h left; rule is 'fewer than 72h')
- Dispute DSP-100185: amex F29 (processor cat: fraudulent), $300.00; issuer msg: ""; 72.0 h left
- Order ORD-101088 total $300.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: USPS Priority Mail, tracking SYN94482335051815, status delivered, addr match True, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 400 d old at order; prior orders 2, undisputed+delivered in 120-365d window 2, same device+IP 2; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['avs_cvv_match', 'delivery_confirmation', 'delivered_to_billing_address'] | missing [] | strong ['prior_undisputed_orders', 'device_ip_match', 'established_account'] | conflicts - | fault - | credit_full False | p=0.71 EV=$178.0 | triggers - | **FIGHT** (positive_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### HW-11 - item_not_received / hw_low_amount_conflict (Conflict, but the amount is too small to be worth a human's time)
- Dispute DSP-100187: visa 13.1 (processor cat: product_not_received), $25.00; issuer msg: ""; 456.0 h left
- Order ORD-101092 total $25.00, AVS Y / CVV M, ship==bill True, policy yes, listing snapshot yes
- Shipment: USPS Priority Mail, tracking SYN94824183787423, status delivered, addr match False, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 400 d old at order; prior orders 0, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 0
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['carrier_tracking', 'delivery_confirmation'] | missing ['address_match'] | strong [] | conflicts ['delivered_to_different_address'] | fault - | credit_full False | p=0.168 EV=$-30.8 | triggers ['conflicting_evidence', 'missing_required_evidence'] | **ACCEPT** (negative_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

### HW-12 - fraud / hw_repeat_disputer_small (Repeat disputer, weak evidence, small amount)
- Dispute DSP-100191: mastercard 4837 (processor cat: fraudulent), $40.00; issuer msg: ""; 813.0 h left
- Order ORD-101096 total $40.00, AVS U / CVV N, ship==bill False, policy yes, listing snapshot yes
- Shipment: UPS Ground, tracking SYN1Z207255483284, status delivered, addr match True, sig False, photo False, dispatch photo False; last event: Delivered, left at front door
- Customer: account 410 d old at order; prior orders 3, undisputed+delivered in 120-365d window 0, same device+IP 0; other disputes 3
- Refunds: $0.00; returns: none
- Messages:
- **Label**: present ['delivery_confirmation'] | missing ['avs_cvv_match', 'delivered_to_billing_address'] | strong ['established_account'] | conflicts - | fault - | credit_full False | p=0.15 EV=$-29.0 | triggers ['repeat_disputer', 'missing_required_evidence'] | **ACCEPT** (negative_expected_value)
- Reviewer verdict: [ ] agree  [ ] disagree - note:

