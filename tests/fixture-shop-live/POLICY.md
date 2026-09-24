# Shop policy — the written rules the code is supposed to implement

These are the shop's own decisions. They are not a specification of the code; they are what the
owner has told customers, which is what the code has to match.

## Stock

1. A unit is held for a customer from the moment the order is placed, not from payment.
2. The hold lasts **30 minutes**. After that the unit goes back on sale automatically.
3. Stock is never negative. A customer who asks for more than exists is told so, in a sentence,
   on the page they were on.

## Payment

4. An order becomes paid only when the provider's signed notification says so.
5. A declined payment releases the unit immediately.
6. The provider may send the same notification more than once; the shop's answer must be the
   same every time, and so must the shop's state.

## Refunds

7. An operator may refund any paid order.
8. **A refund within 30 days returns the unit to stock**, because the goods come back. A refund
   after 30 days does not; by then the piece has usually been kept.
9. The customer is told when a refund is recorded.

## Telling people things

10. Anything the shop cannot do for a customer is said to that customer on the page, in words.
11. Anything an operator has to deal with appears on the admin order screen. A log file is not
    an operator screen.
