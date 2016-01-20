/* a very simplified version of a Forth text interpreter

   Input: A sequence of the following:
   
   1) '\n' (line feed) followed by a character identifying a wordlist
      followed by a name: define the name in the wordlist
   2) '\t' (tab) followed by a sequence of characters:
      set the search order; the bottom of the search order is first,
      the top last
   3) ' ' (space) followed by a name:
      look up the name in the search order; there may be names that are
       not in the search order.

   Names do not contain characters <= ' ', and these characters are
   also not used for identifying wordlists.

   To verify that these things work, every defined word gets a serial
   number (starting with 1) and a hash is computed across all found
   words */

#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdio.h>
#include <sys/mman.h>
#include <string.h>

/* a wordlist is organized as a linked list, so you can reorganize it
   as you see fit */
typedef struct list_entry {
  struct list_entry *next;
  unsigned char *name;
  size_t name_len;
  unsigned long serialno;
} list_entry;

/* each wordlist is identified by a character, used as indexes into
   the following array */
list_entry *wordlists[256];
list_entry sentinel;

/* the search order is a sequence of characters, starting with the
   bottom, represented with the pointer and length here */
unsigned char *order;
size_t order_len;

/* insert name starting at s+1 (and ending at the next char <=' ')
   into the wordlist given at *s, associate serialno with it; return
   the first character after the name */
unsigned char *create(unsigned char *s, unsigned long serialno) {
  unsigned char w=*s++;
  size_t i;
  list_entry *new = malloc(sizeof(list_entry));
  for (i=0; s[i]>' '; i++)
    ;
  new->next = wordlists[w];
  new->name = s;
  new->name_len = i;
  new->serialno = serialno;
  wordlists[w] = new;
  return s+i;
}

/* set the search order to the one specified by starting at s, and
   ending at the first character <=' '; return the first character
   after the search order */
unsigned char *set_order(unsigned char *s) {
  order = s;
  for (order_len=0; s[order_len]>' '; order_len++)
    ;
  return order+order_len;
}

/* look up the name starting at s with length s_len in the wordlist
   wl; if successfull, store the serialno of the word in foundp,
   otherwise 0 */
void search_wordlist(unsigned char *s, size_t s_len, list_entry *wl, unsigned long *foundp) {
  for (; ; wl = wl->next) {
    if (s_len == wl->name_len && memcmp(s,wl->name,s_len)==0) {
      *foundp = wl->serialno;
      return;
    }
  }
}

/* look up the name starting at s and ending at the next char <=' ' in
   the search order, storing the serialno of the word in foundp if
   successful, otherwise 0; return the first character after the
   name */
unsigned char *find(unsigned char *s, unsigned long *foundp) {
  size_t i;
  signed long j;
  for (i=0; s[i]>' '; i++)
    ;
  sentinel.name_len = i;
  sentinel.name = s;
  for (j=order_len-1; j>=0; j--) {
    search_wordlist(s,i,wordlists[order[j]],foundp);
    if (*foundp != 0)
      return s+i;
  }
  *foundp = 0;
  return s+i;
}

int main(int argc, char* argv[]) {
  int fd;
  struct stat buf;
  unsigned char *s;
  unsigned long hash = 0;
  unsigned long serialno = 1;
  unsigned long found;
  unsigned long k0=0xb64d532aaaaaaad5;
  if (argc!=2) {
    fprintf(stderr,"Usage: %s <file>\n",argv[0]);
    exit(1);
  }
  fd=open(argv[1], O_RDONLY);
  if (fd==-1) {
    perror(argv[1]);
    exit(1);
  }
  if (fstat(fd, &buf) == -1) {
    perror(argv[1]);
    exit(1);
  }
  s = mmap(NULL, buf.st_size+1, PROT_READ|PROT_WRITE, MAP_PRIVATE, fd, 0);
  s[buf.st_size] = '\0';
  wordlists[0] = &sentinel;
  unsigned short offset = 1, count = 1, ptr_size = sizeof(void *);// sizeof(void *);
  for ( ; offset + count <= 256; offset += count, count *= 2)
    memcpy(wordlists + offset, wordlists, ptr_size*count);
  sentinel.serialno = 0;

  while (*s != '\0') {
    switch (*s++) {
    case '\n': s=create(s,serialno++); break;
    case '\t': s=set_order(s); break;
    case ' ' : 
      { 
        s=find(s,&found);
        if (found!=0) {
          hash=(hash^found)*k0;
          hash^= (hash>>41);
        }
      }
      break;
    default:
      fprintf(stderr,"invalid input");
      exit(1);
    }
  }

  printf("%lx\n",hash);
  return 0;
}


