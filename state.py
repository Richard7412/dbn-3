import copy

from PIL import Image

import utils


class Immutable:
    
    def _copy(self):
        raise NotImplementedError
    
    @staticmethod
    def mutates(function):
        """
        decorator for first duplicating
        """
        def inner_function(old, *args, **kwargs):
            new = copy.copy(old)
            
            # lets do this... attach self to out as predecessor
            if hasattr(new, 'previous'):
                new.previous = old
            
            retval = function(new, *args, **kwargs)
            if not retval:
                return new
            else:
                return retval #trusting them...
            
        return inner_function
        

class DBNCommandSet(Immutable):
    """
    For now, just the built ins (Line, Paper, Pen)
    """
    
    def __init__(self):
        self.dispatch = {
            'Line' : self.Line,
            'Paper' : self.Paper,
            'Pen' : self.Pen,
        }
        
    def __copy__(self):
        return DBNCommandSet() # because the builtins come builtin
    
    def Line(self, state, blX, blY, trX, trY):

        blX = utils.pixel_to_coord(blX, 'x')
        blY = utils.pixel_to_coord(blY, 'y')
        trX = utils.pixel_to_coord(trX, 'x')
        trY = utils.pixel_to_coord(trY, 'y')
        
        points = utils.bresenham_line(blX, blY, trX, trY)
        pixel_list = ((x, y, state.pen_color) for x, y in points)
        
        state.image = state.image.set_pixels(pixel_list)
    
    def Paper(self, state, value):
        color = utils.scale_100(value)
        state.image = DBNImage(color=color)
    
    def Pen(self, state, value):
        color = utils.scale_100(value)
        state.pen_color = color
            
    def run(self, state, command_string, args):
        return self.dispatch[command_string](state, *args)

class DBNInterpreterState(Immutable):
    """
    The state of the interpreter.
    Really, just the pen color, master environment?
    and, of course, the image.
    
    fucking immutable!
    """        
    
    def __init__(self, create=True):
        self.previous = None
        if create:
            self.image = DBNImage(color=255)
            self.pen_color = 0
            self.env = {}
            self.commands = DBNCommandSet()
                    
    def __copy__(self):
        new = DBNInterpreterState(create=False)
        
        # copy all the attributes over
        # this should be sufficient for now
        new.image = copy.copy(self.image)
        new.pen_color = self.pen_color # an integer, so no need to copy
        new.env = copy.copy(self.env)
        new.commands = copy.copy(self.commands)
        
        return new
        
    def lookup_variable(self, var):
        return self.env.get(var, 0)
     
    @Immutable.mutates  
    def set_variable(self, var, to):
        self.env[var] = to
    
    @Immutable.mutates 
    def set(self, lval, rval):
        """
        sets lval to rval
        
        lval can be a DBNDot or a DBNVariable
        """     
        if isinstance(lval, utils.DBNDot):
            x_coord = utils.pixel_to_coord(lval.x, 'x')
            y_coord = utils.pixel_to_coord(lval.y, 'y')
            color = utils.scale_100(rval)
            self.image = self.image.set_pixel(x_coord, y_coord, color)

        elif isinstance(lval, utils.DBNVariable):
            self.env[lval.name] = rval
        
        else:
            raise ValueError("Unknown lvalue! %s" % str(lval))

    @Immutable.mutates
    def run_command(self, command_string, args):
        self.commands.run(self, command_string, args)  
             

class DBNImage(Immutable):
    """
    Primitive wrapper around pil image
    
    in PIL represention, not DBN (255, upper left origin, etc)
    """
    def __init__(self, color=255, create=True):
        if create:
            self._image = Image.new('L', (101, 101), color)
            self._image_array = self._image.load()
        
    def __copy__(self):
         new = DBNImage(create=False)
         new._image = self._image.copy()
         new._image_array = new._image.load()
         return new
    
    def query_pixel(self, x, y):
        return self._image_array[x, y]
    
    def __set_pixel(self, x, y, value):
        if x > 100:
            return False
        if x < 0:
            return False
        
        if y > 100:
            return False
        if y < 0:
            return False
    
        self._image_array[x, y] = value
        return True
    
    @Immutable.mutates
    def set_pixel(self, x, y, value):
        self.__set_pixel(x, y, value)
        
    @Immutable.mutates
    def set_pixels(self, pixel_iterator):
        for x, y, value in pixel_iterator:
            self.__set_pixel(x, y, value)
            

