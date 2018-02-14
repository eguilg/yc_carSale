import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math
import datetime
from keras.models import Model
from keras.layers import Input,Dense,LSTM,Masking,Merge,Concatenate
from keras.wrappers.scikit_learn import KerasRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from sklearn.metrics import make_scorer
from sklearn.model_selection import GridSearchCV
from feature.time_series import load_train_time_series, load_test_time_series
# convert an array of values into a dataset matrix


def create_model(dense_shape,year_seq_shape,month_seq_shape,
                 seq_size = 64, final_dense_size = 32):

    class_dense_input = Input(shape=dense_shape, name='dense_input')
    class_dense_out = Dense(seq_size)(class_dense_input, name='class_dense')

    year_seq_input = Input(shape=year_seq_shape, name='year_seq_input')
    year_seq_mask = Masking(mask_value=-1, input_shape=year_seq_shape,
                            name='year_seq_mask')(year_seq_input)
    year_seq_out = LSTM(seq_size, input_shape=year_seq_shape,
                        dropout_W=0.2, dropout_U=0.2, name='year_seq')(year_seq_mask)

    month_seq_input = Input(shape=month_seq_shape, name='month_seq_input')
    month_seq_mask = Masking(mask_value=-1, input_shape=month_seq_shape,
                             name='year_seq_mask')(month_seq_input)
    month_seq_out = LSTM(seq_size, input_shape=month_seq_shape,
                         dropout_W=0.2, dropout_U=0.2, name='month_seq')(month_seq_mask)

    seq_merge = Merge(layers=[year_seq_out, month_seq_out], name='seq_merge')
    final_merge = Merge(layers=[class_dense_out, seq_merge], name='final_merge')

    final_dense = Dense(final_dense_size)(final_merge)
    main_out = Dense(1)(final_dense)

    model = Model(inputs=[class_dense_input, year_seq_input, month_seq_input],
                  outputs=[main_out])
    model.compile(optimizer='adam', loss='mean_square_loss')
    model.summary()
    return model

def _scorer(ground_truth, pred):
    return mean_squared_error(ground_truth, pred)
    # return mean_squared_error(np.expm1(ground_truth), np.expm1(pred))
if __name__ == '__main__':
    YEAR_SEQ_LEN = 3
    MONTH_SEQ_LEN = 6

    NUM_EPOCH = 500
    BATCH_SIZE = 300
    sale_quantity, class_feature_train, year_seq_train, month_seq_train = load_train_time_series(lb_year=YEAR_SEQ_LEN,
                                                                               lb_mon=MONTH_SEQ_LEN)

    class_feature_test, year_seq_test, month_seq_test =load_test_time_series(lb_year=YEAR_SEQ_LEN,
                                                                               lb_mon=MONTH_SEQ_LEN)
    # fix random seed for reproducibility
    np.random.seed(7)
    # load the dataset
    # dataframe = read_csv('international-airline-passengers.csv', usecols=[1], engine='python', skipfooter=3)
    Y_train = sale_quantity
    X1_train = class_feature_train
    X2_train = year_seq_train
    X3_train = month_seq_train
    print(X1_train.shape,X2_train.shape,X3_train.shape)
    X1_test = class_feature_test
    X2_test = year_seq_test
    X3_test = month_seq_test
    print(X1_test.shape, X2_test.shape, X3_test.shape)

    # normalize the dataset
    scalerX1 = MinMaxScaler(feature_range=(0, 1))
    scalerX2 = MinMaxScaler(feature_range=(0, 1))
    scalerX3 = MinMaxScaler(feature_range=(0, 1))
    scalerY = MinMaxScaler(feature_range=(0, 1))

    X1_train = scalerX1.fit_transform(X1_train)
    X2_train = scalerX2.fit_transform(X2_train)
    X3_train = scalerX3.fit_transform(X3_train)
    Y_train = scalerY.fit_transform(np.reshape(Y_train,(-1,1)))

    X1_test = scalerX1.transform(X1_test)
    X2_test = scalerX2.transform(X2_test)
    X3_test = scalerX3.transform(X3_test)
    # split into train and vali sets
    # train_size = int(len(X1_train) * 0.80)
    # vali_size = len(X1_train) - train_size
    # trainX, valiX = X[0:train_size,:], X[train_size:len(X),:]
    # trainY, valiY = Y[0:train_size,:], Y[train_size:len(Y),:]


    # reshape input to be [samples, time steps, features]
    X2_train = np.reshape(X2_train, (X2_train.shape[0], YEAR_SEQ_LEN,int(X2_train.shape[1]/YEAR_SEQ_LEN)))
    X3_train = np.reshape(X3_train, (X3_train.shape[0],YEAR_SEQ_LEN,int(X3_train.shape[1]/YEAR_SEQ_LEN)))

    X2_test = np.reshape(X2_test, (X2_test.shape[0], YEAR_SEQ_LEN, int(X2_test.shape[1] / YEAR_SEQ_LEN)))
    X3_test = np.reshape(X3_test, (X3_test.shape[0], YEAR_SEQ_LEN, int(X3_test.shape[1] / YEAR_SEQ_LEN)))
    # create and fit the LSTM network

    model = KerasRegressor(build_fn=create_model, nb_epoch=NUM_EPOCH, batch_size=BATCH_SIZE, verbose=2)

    grid = dict(
        dense_shape=[(X1_train.shape[1])],
        year_seq_shape = [(X2_train.shape[1], X2_train.shape[2])],
        month_seq_shape = [(X3_train.shape[1], X2_train.shape[2])],
        seq_size = [32,64,128],
        final_dense_size = [32,64,128]
    )
    grid = GridSearchCV(estimator=model, param_grid=grid, n_jobs=-1,cv=6,refit=True,
                        scoring=make_scorer(_scorer,greater_is_better=False))

    cv = grid.fit((X1_train,X2_train,X3_train), (Y_train))
    # model.fit([X1_train,X2_train,X3_train], [Y_train], epochs=NUM_EPOCH, batch_size=BATCH_SIZE, verbose=2)
    # make predictions
    # trainPredict = model.predict(trainX)
    # valiPredict = model.predict(valiX)

    # totallY = np.vstack((trainPredict,valiPredict))
    # inversedY = scalerY.inverse_transform(totallY)
    #
    # trainPredict,valiPredict = inversedY[0:train_size,:], inversedY[train_size:len(inversedY),:]
    # Y = scalerY.inverse_transform(Y)
    #
    # trainY, valiY = Y[0:train_size,:], Y[train_size:len(Y),:]
    # trainScore = math.sqrt(mean_squared_error(trainY[:], trainPredict[:,0]))
    # print('Train Score: %.2f rmse' % (trainScore))
    # valiScore = math.sqrt(mean_squared_error(valiY[:], valiPredict[:,0]))
    # print('vali Score: %.2f rmse' % (valiScore))
    # shift train predictions for plotting
    # fig = plt.figure()
    # ax1=fig.add_subplot(211)
    # ax1.plot(trainPredict,label='pred')
    # ax1.plot(trainY,label='true',alpha =0.5)
    # ax1.legend(['pred','true'])
    # ax1.set_title('train')
    # ax2 = fig.add_subplot(212)
    # ax2.set_title('vali')
    # ax2.plot(valiPredict,label = 'pred')
    # ax2.plot(valiY, label = 'true',alpha =0.5)
    # ax2.legend(['pred','true'])
    #
    # plt.show()




    testPredict = cv.predict([X1_test,X2_train,X3_test])
    testPredict = scalerY.inverse_transform(testPredict)

    sub = pd.read_csv('../data/yancheng_testA_20171225.csv')
    sub.predict_quantity = np.reshape(testPredict,(testPredict.shape[0]))
    timestamp = datetime.datetime.now().strftime('%m%d%H%M')
    sub.to_csv('../sub/lstm_y'+str(YEAR_SEQ_LEN)+'m'+str(MONTH_SEQ_LEN)+'_'+'e'+str(NUM_EPOCH)+'b'+str(BATCH_SIZE)+'_'+timestamp+'.csv',index=False)