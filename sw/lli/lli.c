#include <avr/io.h>
#include <util/delay.h>
 
 
int main (void)
{
  /* set PORTB.5 for output*/
  DDRB = (1<<PB5);
  DDRB = (1<<PB7);
 
  while (1)
    {
      /* flip PORTB.2 */
      PORTB ^= (1<<PB5);
      PORTB ^= (1<<PB7);
	  	_delay_ms(100);
    }
 
  return 1;
}
