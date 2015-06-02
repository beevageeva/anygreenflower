import re

def requiredErrorMessage(paramname):
	return "El valor de %s es requerido" % paramname	

#valFunc must be a function taking one param and return [False, ErrorMessage] or [True]
#this function will return [False, [errors]] or [True]
def validateForm(params, fieldsConditions={}):
		errors = []
		for key in fieldsConditions:
			listfunc = fieldsConditions[key]
			if not type(listfunc) is list:
				listfunc = [listfunc]
			for valFunc in listfunc:
				if key in params:
					paramValue = params[key]
					ret = valFunc(paramValue)
					if(not ret[0]):
						errors.append("Error para el campo %s: %s" % (key, ret[1]))
				else:
					errors.append(requiredErrorMessage(key))
		if(len(errors)==0):
			return [True]
		else:
			return [False, errors]


def checkRange(value, minValue, maxValue):
	if(minValue<=value and value <=maxValue):
		return [True]
	else:
		return [False, "El valor tiene que ser entre "+ str(minValue) + " y " + str(maxValue) + ", el valor introducido es: " + str(value)]


def minLength(minValue):
	def checkMinLength(paramValue):
		if(len(paramValue)<minValue):
			return [False, "El campo tiene que tener minimo %d caracteres" % minValue]
		return [True]
	return checkMinLength

def maxLength(maxValue):
	def checkMaxLength(paramValue):
		if(len(paramValue)>maxValue):
			return [False, "El campo tiene que tener maximo %d caracteres" % maxValue]
		return [True]
	return checkMaxLength

def lengthBetween(minValue, maxValue):
	def checkLengthBetween(paramValue):
		if(len(paramValue)>maxValue or len(paramValue)<minValue):
			return [False, "El campo tiene que tener minimo %d y maximo %d caracteres" %(minValue, maxValue)]
		return [True]
	return checkLengthBetween

def intRangeField(minValue, maxValue):
	def checkIntRangeField(paramValue):
		try:
			intParamValue = int(paramValue)
		except ValueError:
			return [False, "El valor tiene que ser entero"]
		return checkRange(intParamValue, minValue, maxValue)
	return checkIntRangeField
		
def floatRangeField(minValue, maxValue):
	def checkFloatRangeField(paramValue):
		try:
			floatParamValue = float(paramValue)
		except ValueError:
			return [False, "El valor tiene que ser float"]
		return checkRange(intParamValue, minValue, maxValue)
	return checkFloatRangeField	

def floatField():
	def checkFloatField(paramValue):
		try:
			floatParamValue = float(paramValue)
		except ValueError:
			return [False, "El valor tiene que ser float"]
		return [True]
	return checkFloatField	

def intField():
	def checkIntField(paramValue):
		try:
			intParamValue = int(paramValue)
		except ValueError:
			return [False, "El valor tiene que ser entero"]
		return [True]
	return checkIntField	

def regExpMatch(pattern):
	def checkRegExpMatch(paramValue):
		if re.compile(pattern).match(paramValue):
			return [True]
		else:
			return [False, "El campo tiene que tener la forma: %s" % pattern]
	return checkRegExpMatch


