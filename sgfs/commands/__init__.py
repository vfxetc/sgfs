import optparse
import os

from sgfs import SGFS


class Command(object):

    def __init__(self):
        
        doc = self.__class__.__doc__ or '%prog options'
        doc = doc.splitlines()
        self.opt_parser = optparse.OptionParser(
            usage=doc[0].strip(),
            description='\n'.join(doc[1:]).rstrip(),
        )
        
        self.add_option = self.opt_parser.add_option
        self.print_usage = self.opt_parser.print_usage
        
        self.add_option('--root', dest='root', help='SGFS project root', default=os.environ.get('SGFS_ROOT', '.'))
        
    def run(self, sgfs, opts, args):
        raise NotImplementedError()
    
    def __call__(self, *call_args, **kwargs):
        
        opts, args = self.opt_parser.parse_args()
        sgfs = SGFS(root=opts.root)
        
        return self.run(sgfs, opts, args, *call_args, **kwargs)