package com.qyh.agent;

import java.lang.instrument.ClassFileTransformer;
import java.lang.instrument.IllegalClassFormatException;
import java.lang.String;
import java.security.ProtectionDomain;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReferenceArray;

import javassist.CannotCompileException;
import javassist.ClassPool;
import javassist.CtClass;
import javassist.CtMethod;
import javassist.NotFoundException;
import javassist.bytecode.CodeAttribute;
import javassist.bytecode.LocalVariableAttribute;

import java.io.File;
import java.io.FileWriter;

public class ClassTransformer implements ClassFileTransformer {
    private String instLogFile;
    private String runLogFile;
    private String classesPath;

    public static final int MAX_NUM = 1024 * 32;
    private final static AtomicInteger index = new AtomicInteger(0);
    /**
     * key: hashcode
     * value: methodId
     */
    private final static Map<Integer, Integer> methodInfos = new ConcurrentHashMap<>();
    private final static AtomicReferenceArray<Method> methodTagArr = new AtomicReferenceArray<>(MAX_NUM);
    private final static HashSet<Integer> runedMethods = new HashSet<Integer>();

    public ClassTransformer(String outputDir, String classesPath) {
        this.instLogFile = outputDir + File.separator + "inst.log";
        this.runLogFile = outputDir + File.separator + "run.log";
        this.classesPath = classesPath;
    }

    @Override
    public byte[] transform(ClassLoader loader, String className, Class<?> classBeingRedefined,
            ProtectionDomain protectionDomain, byte[] classfileBuffer) throws IllegalClassFormatException {

        // only transform classes in classesPath
        if (!protectionDomain.getCodeSource().getLocation().getPath().contains(classesPath)) {
            return null;
        }

        try {
            // solve className, consider inner class
            className = className.replace("/", ".");
            ClassPool pool = ClassPool.getDefault();
            CtClass ctClass = pool.get(className);
            CtMethod[] cms = ctClass.getDeclaredMethods();
            for (CtMethod cm : cms) {
                transformMethod(cm);
            }
            return ctClass.toBytecode();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }
    

    public static int generateMethodId(Integer hashcode, String clazzName, String methodName,
            List<String> parameterNameList, List<String> parameterTypeList, String returnType) {
        if (methodInfos.containsKey(hashcode)) {
            return methodInfos.get(hashcode);
        }

        Method method = new Method();
        method.setClassName(clazzName);
        method.setMethodName(methodName);
        method.setParameterNameList(parameterNameList);
        method.setParameterTypeList(parameterTypeList);
        method.setReturnType(returnType);

        int methodId = index.getAndIncrement();
        if (methodId > MAX_NUM) {
            return -1;
        }
        methodTagArr.set(methodId, method);
        methodInfos.put(hashcode, methodId);
        return methodId;
    }


    private void transformMethod(CtMethod method)
            throws CannotCompileException, NotFoundException {

        // parameterTypeList
        List<String> parameterTypeList = new ArrayList<>();
        for (CtClass parameterType : method.getParameterTypes()) {
            parameterTypeList.add(parameterType.getName());
        }

        // parameterNameList
        List<String> parameterNameList = new ArrayList<>();
        CodeAttribute codeAttribute = method.getMethodInfo().getCodeAttribute();
        // if abstract or native method, codeAttribute will be null
        if (codeAttribute == null) {
            return;
        }

        LocalVariableAttribute attribute = (LocalVariableAttribute) codeAttribute
            .getAttribute(LocalVariableAttribute.tag);
        for (int i = 0; i < parameterTypeList.size(); i++) {
            parameterNameList.add(attribute.variableName(i));
        }

        CtClass declaringClass = method.getDeclaringClass();
        String signature = declaringClass.getName() + "." + method.getName() + method.getSignature();
        int idx = generateMethodId(signature.hashCode(), declaringClass.getName(), method.getName(),
                parameterNameList, parameterTypeList, method.getReturnType().getName());
        
        try {
            FileWriter fw = new FileWriter(instLogFile, true);
            fw.write(methodTagArr.get(idx).toString() + "\n");
            fw.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
        method.insertBefore("com.qyh.agent.ClassTransformer.point(" + idx + ",\"" + runLogFile + "\");");
    }

    public static void point(final int methodId, final String runLogFile) {
        if (runedMethods.contains(methodId)) {
            return;
        }
        runedMethods.add(methodId);
        Method method = methodTagArr.get(methodId);
        try {
            FileWriter fw = new FileWriter(runLogFile, true);
            fw.write(method.toString() + "\n");
            fw.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
