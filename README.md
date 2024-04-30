# One-time purchase Model POC Documentation and Description

#### FOR A COMPREHENSIVE VIEWING OF ALL CHANGES MADE:


Please visit:  https://github.com/l1scientific/onetimepurchase_POC/compare/5efc8a5..2ab2768

The following are descriptions and small example code blocks on the changes made for the one-time purchase POC.

This app was forked over from the existing subscription model POC, and thus you will notice most of the changes are removals from the subscription model app.

### Changes in `intent_helper`
- Changed the welcome message to refer to the proper app title (one-time purchase instead of subscription)
- Removed all subscription end date calculation features
- Changed the logic to make it so that if you do not own any products, it gives you a 'free version' welcome message, and if you DO own a product, if gives you a 'paid version' welcome message

### Changes in `lambda_function`
- Removed feature to differentiate between two products to purchase - made it so you can only purchase one product
- Removed the different handling cases for subscription end dates in the connections.response function

### Changes to interaction model
- Changed all subscription utterances to 'product' utterances
- Removed all slot type utterances

