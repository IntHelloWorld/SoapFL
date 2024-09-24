package com.qyh.agent;

import java.util.List;
import org.apache.commons.lang3.StringUtils;

public class Method {
    private String className;
    private String methodName;
    private List<String> parameterNameList;
    private List<String> parameterTypeList;
    private String returnType;

    public Method() {
    }

    public Method(String className, String methodName, List<String> parameterNameList,
            List<String> parameterTypeList, String returnType) {
        this.className = className;
        this.methodName = methodName;
        this.parameterNameList = parameterNameList;
        this.parameterTypeList = parameterTypeList;
        this.returnType = returnType;
    }

    public String toString() {
        StringBuffer sb = new StringBuffer();
        sb.append(className + " " + methodName + "(");
        sb.append(StringUtils.join(parameterTypeList, ","));
        sb.append(") " + returnType);
        return sb.toString();
    }

    public String getClassName() {
        return className;
    }

    public String getMethodName() {
        return methodName;
    }

    public List<String> getParameterNameList() {
        return parameterNameList;
    }

    public List<String> getParameterTypeList() {
        return parameterTypeList;
    }

    public String getReturnType() {
        return returnType;
    }

    public void setClassName(String className) {
        this.className = className;
    }

    public void setMethodName(String methodName) {
        this.methodName = methodName;
    }

    public void setParameterNameList(List<String> parameterNameList) {
        this.parameterNameList = parameterNameList;
    }

    public void setParameterTypeList(List<String> parameterTypeList) {
        this.parameterTypeList = parameterTypeList;
    }

    public void setReturnType(String returnType) {
        this.returnType = returnType;
    }

}
